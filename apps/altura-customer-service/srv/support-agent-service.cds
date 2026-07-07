using { CustomerRequestsService } from './customer-requests-service';

@mcp
@mcp.instructions: 'Use describe to explore the service model. Use query to read CustomerRequests, Tasks, and Equipment. Use get_customer_requests to retrieve by customer_id, and list_latest_customer_requests to see the 20 most recent requests.'
service SupportAgentService {

  @title: 'Customer Requests'
  @description: 'Customer service requests with associated tasks and equipment'
  entity CustomerRequests as projection on CustomerRequestsService.CustomerRequests {
    ID, createdAt,
    customer_id, contact_name, contact_email, country,
    request_summary, urgency, relevance,
    tasks
  };

  @description: 'Service tasks linked to a customer request'
  entity Tasks as projection on CustomerRequestsService.Tasks {
    ID, parent,
    address, country, postal_code, relevance,
    equipment
  };

  @description: 'Equipment items associated to a service task'
  entity Equipment as projection on CustomerRequestsService.Equipment {
    ID, parent, name
  };

  @description: 'Lists the 20 latest customer service requests ordered by creation date'
  function list_latest_customer_requests() returns array of CustomerRequests;

  @description: 'Retrieves customer service requests for a specific customer by customer_id'
  action get_customer_requests(
    customer_id : String @description: 'Customer identifier, e.g. ai-integrations-000'
  ) returns array of CustomerRequests;
}
