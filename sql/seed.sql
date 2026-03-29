USE travel_app;

DELETE FROM PlaceCategory;
DELETE FROM TripListItem;
DELETE FROM Review;
DELETE FROM TripList;
DELETE FROM Category;
DELETE FROM Place;
DELETE FROM User;

ALTER TABLE User AUTO_INCREMENT = 1;
ALTER TABLE Place AUTO_INCREMENT = 1;
ALTER TABLE Review AUTO_INCREMENT = 1;
ALTER TABLE TripList AUTO_INCREMENT = 1;
ALTER TABLE Category AUTO_INCREMENT = 1;

INSERT INTO User (Username, Email, PasswordHash, DisplayName, Role) VALUES
('samuel14', 'samuel14@example.com', 'hashed_password_1', 'Samuel Lee', 'tourist'),
('miachan', 'miachan@example.com', 'hashed_password_2', 'Mia Chan', 'tourist'),
('owenwang', 'owenwang@example.com', 'hashed_password_3', 'Owen Wang', 'business_owner'),
('admin01', 'admin01@example.com', 'hashed_password_4', 'Site Admin', 'admin');

INSERT INTO Category (TagName) VALUES
('Park'),
('Restaurant'),
('Cafe'),
('Museum'),
('Hotel'),
('Mall'),
('Attraction');

-- Sample Vancouver places
INSERT INTO Place (Name, Description, Address, Hours, ContactInfo, Website, AvgRating, IsActive) VALUES
('Stanley Park', 'Large public park with scenic seawall, trails, and landmarks.', 'Vancouver, BC', '06:00-22:00', '604-555-1001', 'https://vancouver.ca/parks/stanley-park', 4.8, TRUE),
('Granville Island Public Market', 'Popular market with local food vendors and artisan shops.', '1689 Johnston St, Vancouver, BC', '09:00-19:00', '604-555-1002', 'https://granvilleisland.com', 4.6, TRUE),
('Vancouver Art Gallery', 'Major art museum in downtown Vancouver.', '750 Hornby St, Vancouver, BC', '10:00-17:00', '604-555-1003', 'https://www.vanartgallery.bc.ca', 4.4, TRUE),
('Capilano Suspension Bridge Park', 'Suspension bridge attraction with forest views.', '3735 Capilano Rd, North Vancouver, BC', '10:00-18:00', '604-555-1004', 'https://www.capbridge.com', 4.7, TRUE),
('Metrotown Mall', 'Large shopping mall with retail stores and dining.', '4700 Kingsway, Burnaby, BC', '10:00-21:00', '604-555-1005', 'https://www.metropolisatmetrotown.com', 4.2, TRUE),
('Cafe Medina', 'Popular brunch cafe known for waffles and Mediterranean-inspired dishes.', '780 Richards St, Vancouver, BC', '08:00-15:00', '604-555-1006', 'https://cafemedina.ca', 4.5, TRUE),
('Fairmont Hotel Vancouver', 'Luxury downtown hotel near major attractions.', '900 W Georgia St, Vancouver, BC', '24 Hours', '604-555-1007', 'https://www.fairmont.com', 4.6, TRUE),
('Science World', 'Interactive science museum for families and visitors.', '1455 Quebec St, Vancouver, BC', '10:00-17:00', '604-555-1008', 'https://www.scienceworld.ca', 4.3, TRUE);

-- Place-category mappings
INSERT INTO PlaceCategory (PlaceID, CategoryID) VALUES
(1, 1), -- Stanley Park -> Park
(1, 7), -- Stanley Park -> Attraction
(2, 7), -- Granville Island -> Attraction
(3, 4), -- Vancouver Art Gallery -> Museum
(3, 7), -- Vancouver Art Gallery -> Attraction
(4, 7), -- Capilano -> Attraction
(5, 6), -- Metrotown -> Mall
(6, 2), -- Cafe Medina -> Restaurant
(6, 3), -- Cafe Medina -> Cafe
(7, 5), -- Fairmont -> Hotel
(8, 4), -- Science World -> Museum
(8, 7); -- Science World -> Attraction

-- Sample reviews
INSERT INTO Review (UserID, PlaceID, Rating, Title, Body) VALUES
(1, 1, 5, 'Amazing day out', 'Beautiful views and a great walk along the seawall.'),
(2, 1, 4, 'Relaxing and scenic', 'Very nice park, but parking was a bit hard to find.'),
(1, 2, 5, 'Loved the market', 'Great variety of food and a lively atmosphere.'),
(2, 3, 4, 'Nice gallery visit', 'Interesting exhibits and a convenient downtown location.'),
(1, 6, 5, 'Excellent brunch', 'The waffles were great and service was quick.'),
(2, 8, 4, 'Fun for families', 'Interactive exhibits made it a fun afternoon.');

-- Sample trip lists
INSERT INTO TripList (UserID, Title, Description, IsPublic) VALUES
(1, 'Best First-Time Vancouver Spots', 'Places I would recommend to first-time visitors.', TRUE),
(2, 'Weekend Indoor Ideas', 'Good options for rainy Vancouver weekends.', TRUE),
(1, 'Food and Views Day Plan', 'A simple one-day list with food and scenic stops.', FALSE);

-- Trip list items
INSERT INTO TripListItem (ListID, PlaceID, Position, Note) VALUES
(1, 1, 1, 'Start the morning with a seawall walk.'),
(1, 2, 2, 'Grab lunch here after Stanley Park.'),
(1, 4, 3, 'Visit in the afternoon for the bridge views.'),
(2, 3, 1, 'Good downtown indoor stop.'),
(2, 8, 2, 'Great choice for a rainy day.'),
(2, 5, 3, 'Shopping and food options nearby.'),
(3, 6, 1, 'Breakfast stop.'),
(3, 1, 2, 'Scenic walk after brunch.');

UPDATE Place p
SET AvgRating = (
    SELECT ROUND(AVG(r.Rating), 1)
    FROM Review r
    WHERE r.PlaceID = p.PlaceID
)
WHERE EXISTS (
    SELECT 1
    FROM Review r
    WHERE r.PlaceID = p.PlaceID
);

