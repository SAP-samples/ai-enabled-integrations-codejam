namespace altura;

using { cuid, managed } from '@sap/cds/common';

entity CustomerRequests : cuid, managed {
  customer_id      : String(50);
  contact_name     : String(100);
  contact_email    : String(150);
  @assert.format: '^[A-Z]{2}$'
  @assert.format.message: 'country must be a valid ISO 3166-1 alpha-2 code (e.g. DE, ES, FR)'
  country          : String(2);
  request_original : LargeString;
  request_summary  : LargeString;
  urgency          : String(20);  // 'High' | 'Medium' | 'Low'
  @assert.range: [0, 10]
  @assert.range.message: 'relevance must be between 0 and 10'
  relevance        : Integer;
  tasks            : Composition of many Tasks on tasks.parent = $self;
}

entity Tasks : cuid {
  parent      : Association to CustomerRequests;
  address     : String(500);
  @assert.format: '^[A-Z]{2}$'
  @assert.format.message: 'country must be a valid ISO 3166-1 alpha-2 code (e.g. DE, ES, FR)'
  country     : String(2);
  postal_code : String(20);
  @assert.range: [0, 10]
  @assert.range.message: 'relevance must be between 0 and 10'
  relevance   : Integer;
  equipment   : Composition of many Equipment on equipment.parent = $self;
}

entity Equipment : cuid {
  parent : Association to Tasks;
  name   : String(200);
}
