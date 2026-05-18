# Validity Checker

Usage:
Linux:    ./validity_checker cities.txt solution.txt
Windows:  validity_checker.exe cities.txt solution.txt

Input format:
Cities:    name, latitude, longitude
Solution:  latitude, longitude, radius

Output:
- OK: all cities are covered
- NOT_FEASIBLE: prints one uncovered city
- INPUT_ERROR: if format is invalid