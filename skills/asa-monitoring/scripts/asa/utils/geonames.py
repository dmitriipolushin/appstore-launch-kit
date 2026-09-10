import requests

def get_popular_countries():
    return [ # use GPT for this task
        "France", "Spain", "United States", "China", "Italy", "Mexico", "Thailand", 
        "Germany", "United Kingdom", "Turkey", "Japan", "Canada", "Australia", 
        "India", "Brazil", "Russia", "South Korea", "Indonesia", "Netherlands", 
        "Switzerland", "Greece", "Portugal", "Austria", "Malaysia", "Singapore", 
        "South Africa", "Argentina", "Vietnam", "Philippines", "Egypt", 
        "Morocco", "New Zealand", "Ireland", "Belgium", "Sweden", 
        "Norway", "Denmark", "Poland", "Czech Republic", "Hungary",
        "Finland", "Chile", "Colombia", "Peru", "Israel",
        "Croatia", "Slovakia", "Slovenia", "Iceland",
        "Cambodia", "Estonia",  "Lithuania",
        "Fiji","Laos","Kazakhstan","Paraguay",
        "Trinidad & Tobago","Vanuatu","Bhutan","Cameroon",
        "Costa Rica", "Sri Lanka", "Tanzania", "Kenya", "Uganda", "Ethiopia", 
        "Nepal", "Bulgaria", "Romania", "Cyprus", "Jordan", "Lebanon", 
        "Oman", "Qatar", "United Arab Emirates", "Saudi Arabia", "Bahrain", 
        "Georgia", "Armenia", "Azerbaijan", "Mongolia", "Myanmar", "Maldives", 
        "Seychelles", "Mauritius", "Namibia", "Botswana", "Zambia", "Zimbabwe", 
        "Ghana", "Senegal", "Côte d'Ivoire", "Gabon", "Ecuador", "Uruguay", 
        "Bolivia", "Nicaragua", "Panama", "Dominican Republic", "Cuba", 
        "Jamaica", "Barbados", "Saint Lucia", "Antigua and Barbuda", "Grenada"
    ]

def get_popular_cities(country_name: str, limit: int = 50):
    """
    Get popular cities in a specified country using GeoNames API.
    
    Args:
        country_name (str): Name of the country
        limit (int): Number of cities to return (default: 10)
        
    Returns:
        list: List of popular cities in the country
    """
    # Configuration for GeoNames API
    username = "sharrikk"  # You should register for your own username at geonames.org
    
    # Get country code for the provided country name
    country_url = f"http://api.geonames.org/searchJSON?q={country_name}&maxRows=10&username={username}"
    country_response = requests.get(country_url)
    country_data = country_response.json()
    
    if not country_data.get('geonames'):
        print(f"Country '{country_name}' not found")
        return None
    
    country_code = next((item['countryCode'] for item in country_data.get('geonames', []) if 'countryCode' in item), None)
    if not country_code:
        print(f"Country '{country_name}' not found")
        return None
    
    # Get popular cities in the country (sorted by population, which is a good proxy for popularity)
    cities_url = f"http://api.geonames.org/searchJSON?country={country_code}&featureClass=P&orderby=population&maxRows={limit}&username={username}"
    cities_response = requests.get(cities_url)
    cities_data = cities_response.json()
    
    # Extract city names
    popular_cities = []
    for city in cities_data.get('geonames', []):
        popular_cities.append({
            'name': city['name'],
            'population': city.get('population'),
            'latitude': city.get('lat'),
            'longitude': city.get('lng')
        })
    
    return popular_cities