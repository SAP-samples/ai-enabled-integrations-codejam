namespace altura.servicelocator;

entity ServiceCenters {
  key ID       : UUID;
      name     : String(100) not null;
      address  : String(200) not null;
      city     : String(100) not null;
      country  : String(100) not null;
      phone    : String(30);
      email    : String(100);
      latitude : Decimal(10, 7) not null;
      longitude: Decimal(10, 7) not null;
}
