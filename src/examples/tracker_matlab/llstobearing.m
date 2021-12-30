% See https://www.movable-type.co.uk/scripts/latlong.html - "Destination point given distance and bearing from start point"
% Equatorial radius of Earth, as specified by the International Union of Geodesy and Geophysics (IUGG)

function [bearing, elevation] = llstobearing(lat0, lng0, alt0, lat1, lng1, alt1)
    lat0_rad = deg2rad(lat0);
    lat1_rad = deg2rad(lat1);
    lng_delta_rad = deg2rad(lng1) - deg2rad(lng0);

    bearing_rad = atan2(...
        +sin(lng_delta_rad) * cos(lat1_rad), ...
        -cos(lng_delta_rad) * cos(lat1_rad) * sin(lat0_rad) + cos(lat0_rad) * sin(lat1_rad));

    elevation_rad = deg2rad(0);

    bearing = mod((rad2deg(bearing_rad) + 360), 360);
    elevation = round(rad2deg(elevation_rad));

end
