sap.ui.define([
    "sap/fe/test/JourneyRunner",
	"customerrequests/test/integration/pages/CustomerRequestsList",
	"customerrequests/test/integration/pages/CustomerRequestsObjectPage"
], function (JourneyRunner, CustomerRequestsList, CustomerRequestsObjectPage) {
    'use strict';

    var runner = new JourneyRunner({
        launchUrl: sap.ui.require.toUrl('customerrequests') + '/test/flpSandbox.html#customerrequests-tile',
        pages: {
			onTheCustomerRequestsList: CustomerRequestsList,
			onTheCustomerRequestsObjectPage: CustomerRequestsObjectPage
        },
        async: true
    });

    return runner;
});

