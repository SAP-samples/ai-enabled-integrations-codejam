using { altura.servicelocator as db } from '../db/schema';

@path: '/service-locator'
service ServiceLocatorService {

  @readonly
  entity ServiceCenters as projection on db.ServiceCenters;

  action getNearestServiceCenter(address : String not null) returns ServiceCenters;
}
