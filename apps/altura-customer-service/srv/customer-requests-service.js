const cds = require('@sap/cds');

module.exports = class CustomerRequestsService extends cds.ApplicationService {
  async init() {
    const { CustomerRequests } = this.entities;

    this.on('get_customer_requests', async (req) => {
      const { customer_id } = req.data;
      if (!customer_id) {
        return req.reject(400, 'customer_id is required');
      }

      const results = await SELECT.from(CustomerRequests)
        .where({ customer_id })
        .columns(c => [
          c`.*`,
          c.tasks(t => [
            t`.*`,
            t.equipment(e => [ e`.*` ])
          ])
        ]);

      return results;
    });

    this.on('list_latest_customer_requests', async () => {
      return await SELECT.from(CustomerRequests).orderBy('createdAt desc').limit(20);
    });

    return super.init();
  }
};
