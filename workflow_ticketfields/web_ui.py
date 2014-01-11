from genshi.builder import tag
from trac.core import *
from trac.config import *
from trac.ticket.api import ITicketActionController
from trac.web.api import IRequestFilter

class WorkflowTicketFieldsModule(Component):

    default_config = {
        "leave": { "status": {"*": "*"} },
        "accept": { "status": {"new": "accepted",
                               "assigned": "accepted",
                               "accepted": "accepted",
                               "reopened": "accepted",
                               }, 
                    "fields": ["owner"],
                    },
        "resolve": { "status": {"new": "closed",
                               "assigned": "closed",
                               "accepted": "closed",
                               "reopened": "closed",
                               },
                    "fields": ["resolution"],
                    },
        "reassign": { "status": {"new": "assigned",
                                 "assigned": "assigned",
                                 "accepted": "assigned",
                                 "reopened": "assigned",
                                 }, 
                      "fields": ["owner"],
                      },
        "reopen": { "status": {"closed": "reopened"},
                    "fields": ["resolution"],
                    "operations": {"resolution": "unset"},
                    },
        "retarget": { "status": {"new": "*",
                                 "assigned": "*",
                                 "accepted": "*",
                                 "reopened": "*",
                                 },
                      "fields": ["milestone"],
                      },
        "escalate": { "status": {"*": "assigned"},
                      "fields": ["owner", "priority", "resolution"],
                      "operations": {"resolution": "unset"},
                      },
        }

    """
    [ticket-workflow-fields]
    leave = * -> *

    accept = new,assigned,accepted,reopened -> accepted
    accept.fields = owner

    resolve = new,assigned,accepted,reopened -> closed
    resolve.fields = resolution

    reassign = new,assigned,accepted,reopened -> assigned
    reassign.fields = owner

    reopen = closed -> reopened
    reopen.fields = resolution
    reopen.fields.resolution.operation = unset

    retarget = new,assigned,accepted,reopened -> *
    retarget.fields = milestone

    escalate = * -> assigned
    escalate.fields = owner,priority,resolution
    escalate.fields.resolution.operation = unset
    """

    ticket_workflow_fields_section = ConfigSection(
        'ticket-workflow-fields',
        """The workflow for tickets is controlled by plugins.""")

    implements(IRequestFilter, ITicketActionController)

    def parse_config(self):
        return self.default_config

    def get_ticket_action_fields(self, req, ticket):
        config = self.parse_config()

        fields = set()
        for weight, action in self.get_ticket_actions(req, ticket):
            fields.update(config[action].get("fields", []))

        return fields

    ## IRequestFilter methods

    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        if template != 'ticket.html':
            return (template, data, content_type)
        if not data.get('ticket'):
            return (template, data, content_type)

        fields = data.get("fields")
        if not fields:
            return (template, data, content_type)

        for field in data['fields']:
            if field['name'] in \
                    self.get_ticket_action_fields(req, data['ticket']):
                field['skip'] = True
        return (template, data, content_type)

    ## ITicketActionController methods

    def get_ticket_actions(self, req, ticket):
        status = ticket._old.get("status", ticket['status']) or 'new'
        
        actions = []
        config = self.parse_config()
        for action in config:
            status_map = config[action]['status']
            if status in status_map:
                actions.append(action)
            elif '*' in status_map:
                actions.append(action)

        return list(enumerate(actions))

    def get_all_status(self):
        all_status = set()
        config = self.parse_config()

        for action in config:
            status_map = config[action]['status']
            for key in status_map:
                all_status.add(key)
                all_status.add(status_map[key])
        all_status.discard('*')
        all_status.discard('')
        return all_status

    def render_ticket_action_control(self, req, ticket, action):
        config = self.parse_config()
        assert action in config

        control = []
        hints = []

        data = config[action]
        
        action_name = action # @@TODO: config'able label/name

        for field in data.get('fields', []):
            id = "action_%s_%s" % (action, field)

            operation = data.get('operations', {}).get(field, "change")
            assert operation in ["change", "unset"]
            if operation == "unset":
                hints.append("%s will be unset" % field) # @@TODO: i18n
                continue
            assert operation == "change"
            current_value = ticket._old.get(field, ticket[field]) or ""
            control.append(tag.label(field,
                                     tag.input(
                        name=id, id=id,
                        type='text', value=current_value)))
            
        current_status = ticket._old.get('status', ticket['status'])
        new_status = data['status'].get(current_status) or \
            data['status']['*']

        if new_status != '*':
            hints.append("Next status will be %s" % new_status) # @@TODO: i18n

        return (action_name, tag(*control), 
                '. '.join(hints) + '.' if hints else '')

    def get_ticket_changes(self, req, ticket, action):
        pass

    def apply_action_side_effects(self, req, ticket, action):
        pass

