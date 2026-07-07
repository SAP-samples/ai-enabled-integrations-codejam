const cds = require('@sap/cds');

module.exports = class SupportAgentService extends cds.ApplicationService {
  async init() {
    const crSrv = await cds.connect.to('CustomerRequestsService');
    const { CustomerRequests, Tasks, Equipment } = this.entities;

    this.on('READ', [CustomerRequests, Tasks, Equipment], (req) => crSrv.run(req.query));

    this.on('list_latest_customer_requests', (req) =>
      crSrv.send('list_latest_customer_requests', req.data)
    );

    this.on('get_customer_requests', (req) =>
      crSrv.send('get_customer_requests', req.data)
    );

    return super.init();
  }
};
