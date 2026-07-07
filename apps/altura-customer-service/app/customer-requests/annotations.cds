using { CustomerRequestsService } from '../../srv/customer-requests-service';

annotate CustomerRequestsService.CustomerRequests with @(
  UI.SelectionFields: [ contact_name, country ],
  UI.PresentationVariant: {
        $Type         : 'UI.PresentationVariantType',
        SortOrder     : [{
            $Type   : 'Common.SortOrderType',
            Property: createdAt,
            Descending: true
        },
        ],
        Visualizations: ['@UI.LineItem'],
    },
  UI.LineItem: [
    { Value: createdAt},
    { Value: customer_id,   Label: 'Customer ID' },
    { Value: contact_name,  Label: 'Contact' },
    { Value: contact_email, Label: 'Email' },
    { Value: country,       Label: 'Country' },
    { Value: urgency,       Label: 'Urgency' }
  ],
  UI.HeaderInfo: {
    TypeName      : 'Request',
    TypeNamePlural: 'Requests',
    Title         : { Value: customer_id },
    Description   : { Value: contact_name }
  },
  UI.FieldGroup #General: {
    Data: [
      { Value: customer_id,   Label: 'Customer ID' },
      { Value: contact_name,  Label: 'Contact' },
      { Value: contact_email, Label: 'Email' },
      { Value: country,       Label: 'Country' },
      { Value: urgency,       Label: 'Urgency' }
    ]
  },
  UI.FieldGroup #Request: {
    Data: [
      { Value: request_summary,  Label: 'Summary' },
      { Value: request_original, Label: 'Original Message' }
    ]
  },
  UI.Facets: [
    {
      $Type : 'UI.ReferenceFacet',
      ID    : 'GeneralInfo',
      Label : 'General Information',
      Target: '@UI.FieldGroup#General'
    },
    {
      $Type : 'UI.ReferenceFacet',
      ID    : 'RequestContent',
      Label : 'Request',
      Target: '@UI.FieldGroup#Request'
    },
    {
      $Type : 'UI.ReferenceFacet',
      ID    : 'TasksFacet',
      Label : 'Tasks',
      Target: 'tasks/@UI.LineItem'
    }
  ]
);

annotate CustomerRequestsService.CustomerRequests with {
  contact_name     @title: 'Contact';
  country          @title: 'Country';
  customer_id      @title: 'Customer ID';
  urgency          @title: 'Urgency';
  contact_email    @title: 'Email';
  request_summary  @title: 'Summary';
  request_original @title: 'Original Message';
};

annotate CustomerRequestsService.Tasks with @(
  UI.LineItem: [
    { Value: address,     Label: 'Address' },
    { Value: country,     Label: 'Country' },
    { Value: postal_code, Label: 'Postal Code' },
    { Value: relevance,   Label: 'Relevance' }
  ],
  UI.HeaderInfo: {
    TypeName      : 'Task',
    TypeNamePlural: 'Tasks',
    Title         : { Value: address }
  },
  UI.FieldGroup #TaskDetails: {
    Data: [
      { Value: address,     Label: 'Address' },
      { Value: country,     Label: 'Country' },
      { Value: postal_code, Label: 'Postal Code' },
      { Value: relevance,   Label: 'Relevance' }
    ]
  },
  UI.Facets: [
    {
      $Type : 'UI.ReferenceFacet',
      ID    : 'TaskDetailsFacet',
      Label : 'Task Details',
      Target: '@UI.FieldGroup#TaskDetails'
    },
    {
      $Type : 'UI.ReferenceFacet',
      ID    : 'EquipmentFacet',
      Label : 'Equipment',
      Target: 'equipment/@UI.LineItem'
    }
  ]
);

annotate CustomerRequestsService.Tasks with {
  address     @title: 'Address';
  country     @title: 'Country';
  postal_code @title: 'Postal Code';
  relevance   @title: 'Relevance';
};

annotate CustomerRequestsService.Equipment with @(
  UI.LineItem: [
    { Value: name, Label: 'Equipment' }
  ],
  UI.HeaderInfo: {
    TypeName      : 'Equipment',
    TypeNamePlural: 'Equipment',
    Title         : { Value: name }
  }
);

annotate CustomerRequestsService.Equipment with {
  name @title: 'Equipment';
};
