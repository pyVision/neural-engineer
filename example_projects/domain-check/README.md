# Domain Sentinel

Domain Sentinel provides automated domain and certificate monitoring. Continuously monitor every domain and associated SSL/TLS certificate in your network for expiration and revocation to avoid downtime and security risks.

Domain Sentinel allows you to track domains and certificates and receive daily updates as well as 30-day critical email alerts before expiry, helping you avoid downtime and mitigate security risks.

# Features

## Domain Monitoring
- Track domain expiration dates
- Receive alerts before domains expire
- Monitor multiple domains from a single dashboard

## SSL/TLS Certificate Monitoring
- Certificate issuance tracking
- Certificate issuer details 
- Certificate expiry date monitoring
- Certificate revocation status checks

## Notifications
- Daily email summary reports
- 30-day warning alerts before expiration
- Critical alerts on certificate or domain expiry

# Getting Started

## Installation

Clone the repository

```bash
git clone https://github.com/yourusername/domain-sentinel.git
cd domain-sentinel
```

## Configuration

Create a `.env` file in the root directory with the following variables:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=domainsentinel
DB_USER=user
DB_PASSWORD=password
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password
ALERT_EMAIL=alerts@example.com
```

## Build and run Docker containers
```bash
docker build -t domain-sentinel:v1 . 
docker run -p 8000:8000 domain-sentinel:v1
```

## Access the dashboard
```
http://localhost:8080
```

# Usage

### Adding Domains to Monitor
1. Log in to the dashboard
2. Navigate to "Domains" section
3. Click "Add Domain" and enter domain details
4. Save changes

## Setting Up Alert Preferences
1. Navigate to "Settings" > "Notifications"
2. Configure email recipients and alert thresholds
3. Save your preferences

## Upcoming Features

- Monitor and track all public certificates including those issued by third-party services
- Detect certificate issuance and installation
- Detect misissued certificates to stay ahead of bad actors
- Automated certificate inventory management with real-time discovery of new certificates
- Certificate Transparency (CT) log monitoring

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the  Apache License - see the [LICENSE](LICENSE) file for details.

## Support

If you encounter any issues or have questions, please file an issue on the GitHub repository.
