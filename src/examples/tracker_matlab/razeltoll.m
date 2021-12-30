% See https://www.movable-type.co.uk/scripts/latlong.html - "Destination point given distance and bearing from start point"
% Equatorial radius of Earth, as specified by the International Union of Geodesy and Geophysics (IUGG)

function [latitude, longitude] = razeltoll(lat0, lng0, range, azimuth, elevation)
    lat0_rad = deg2rad(lat0);
    lng0_rad = deg2rad(lng0);
    az_rad = deg2rad(azimuth);
    el_rad = deg2rad(elevation);
    rng_norm = (cos(el_rad) * range) / 6378137;

    lat_rad = asin(...
        cos(rng_norm) .* sin(lat0_rad) + ...
        sin(rng_norm) .* cos(lat0_rad) .* cos(az_rad));

    lng_rad = lng0_rad + atan2(...
        sin(rng_norm) .* cos(lat0_rad) .* sin(az_rad), ...
        cos(rng_norm) - sin(lat0_rad) .* sin(lat_rad));

    latitude = rad2deg(lat_rad);
    longitude = rad2deg(mod(lng_rad + pi, 2 * pi) - pi);

end
