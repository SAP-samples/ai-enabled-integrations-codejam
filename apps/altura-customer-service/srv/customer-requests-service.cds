using { altura } from '../db/schema';

@path: '/customer-requests'
service CustomerRequestsService {

  entity CustomerRequests as projection on altura.CustomerRequests;
  entity Tasks            as projection on altura.Tasks;
  entity Equipment        as projection on altura.Equipment;

  function list_latest_customer_requests() returns array of CustomerRequests;

  action create_customer_request(
    customer_id     : String,
    contact_name    : String,
    contact_email   : String,
    country         : String,
    urgency         : String,
    request_summary : String
  ) returns CustomerRequests;

  action get_customer_requests(
    customer_id : String
  ) returns array of CustomerRequests;
}
