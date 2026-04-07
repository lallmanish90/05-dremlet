# License Management Guide
## Dreamlet Educational Video Production System

### 🎯 Overview

This guide covers comprehensive license management for the Dreamlet system, including user provisioning, monitoring, and access control.

---

## 🔧 License Server Administration

### Initial Setup

1. **Deploy License Server**
   ```bash
   cd license_server
   docker-compose up -d
   ```

2. **Retrieve Admin API Key**
   ```bash
   docker logs license-server | grep "Admin API Key"
   ```

3. **Secure the Admin Key**
   ```bash
   # Store securely and update docker-compose.yml
   export ADMIN_API_KEY="your_secure_admin_key"
   ```

### User License Management

#### Create New User License

```bash
curl -X POST http://localhost:5000/api/admin/licenses \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "john.doe",
    "email": "john.doe@company.com",
    "company": "Acme Corp",
    "days_valid": 365
  }'
```

**Response:**
```json
{
  "message": "License created successfully",
  "user_id": "john.doe",
  "license_key": "DL_a1b2c3d4_e5f6g7h8",
  "expiry_date": "2025-08-07T10:30:00",
  "days_valid": 365
}
```

#### Batch User Creation

Create `users.json`:
```json
[
  {
    "user_id": "alice.smith",
    "email": "alice.smith@company.com",
    "company": "Acme Corp",
    "days_valid": 180
  },
  {
    "user_id": "bob.johnson",
    "email": "bob.johnson@company.com", 
    "company": "Acme Corp",
    "days_valid": 365
  }
]
```

Batch creation script:
```bash
#!/bin/bash
while IFS= read -r user; do
  curl -X POST http://localhost:5000/api/admin/licenses \
    -H "X-API-Key: $ADMIN_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$user"
  echo
done < users.json
```

### License Operations

#### List All Licenses

```bash
curl -X GET http://localhost:5000/api/admin/licenses \
  -H "X-API-Key: $ADMIN_API_KEY"
```

#### Revoke User License

```bash
curl -X DELETE http://localhost:5000/api/admin/licenses/john.doe \
  -H "X-API-Key: $ADMIN_API_KEY"
```

#### Extend License

```bash
# Extend by 90 days
curl -X PUT http://localhost:5000/api/admin/licenses/john.doe \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"days_extend": 90}'
```

#### Reactivate Revoked License

```bash
curl -X PUT http://localhost:5000/api/admin/licenses/john.doe \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true}'
```

---

## 📊 Monitoring & Analytics

### System Statistics

```bash
curl -X GET http://localhost:5000/api/admin/stats \
  -H "X-API-Key: $ADMIN_API_KEY"
```

**Response:**
```json
{
  "total_licenses": 25,
  "active_licenses": 22,
  "expired_licenses": 3,
  "recent_validations": 147,
  "timestamp": "2024-08-07T10:30:00"
}
```

### Validation Logs

```bash
# Recent validations (last 100)
curl -X GET http://localhost:5000/api/admin/logs?limit=100 \
  -H "X-API-Key: $ADMIN_API_KEY"

# Specific user validations
curl -X GET "http://localhost:5000/api/admin/logs?user_id=john.doe&limit=50" \
  -H "X-API-Key: $ADMIN_API_KEY"
```

### Monitoring Dashboard

Create a simple monitoring script:

```python
#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta

ADMIN_API_KEY = "your_admin_key"
LICENSE_SERVER = "http://localhost:5000"

def get_license_stats():
    response = requests.get(
        f"{LICENSE_SERVER}/api/admin/stats",
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    return response.json()

def get_expiring_licenses(days=30):
    response = requests.get(
        f"{LICENSE_SERVER}/api/admin/licenses",
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    
    licenses = response.json()["licenses"]
    expiring = []
    
    cutoff_date = datetime.now() + timedelta(days=days)
    
    for license in licenses:
        expiry = datetime.fromisoformat(license["expiry_date"])
        if expiry <= cutoff_date and license["is_active"]:
            expiring.append(license)
    
    return expiring

# Generate daily report
stats = get_license_stats()
expiring = get_expiring_licenses()

print(f"License Summary - {datetime.now().strftime('%Y-%m-%d')}")
print("=" * 50)
print(f"Total Licenses: {stats['total_licenses']}")
print(f"Active Licenses: {stats['active_licenses']}")
print(f"Expired Licenses: {stats['expired_licenses']}")
print(f"Recent Validations: {stats['recent_validations']}")
print()
print(f"Licenses Expiring Soon: {len(expiring)}")
for license in expiring:
    print(f"  - {license['user_id']} expires {license['expiry_date']}")
```

---

## 🚨 Incident Response

### Common Scenarios

#### User Reports Access Denied

1. **Check License Status**
   ```bash
   curl -X GET http://localhost:5000/api/admin/licenses \
     -H "X-API-Key: $ADMIN_API_KEY" | jq '.licenses[] | select(.user_id=="problem_user")'
   ```

2. **Check Recent Validation Attempts**
   ```bash
   curl -X GET "http://localhost:5000/api/admin/logs?user_id=problem_user&limit=10" \
     -H "X-API-Key: $ADMIN_API_KEY"
   ```

3. **Common Fixes**
   - License expired: Extend license
   - License revoked: Reactivate license
   - Network issues: Check connectivity
   - Wrong credentials: Verify license key

#### Mass License Issues

1. **Check License Server Health**
   ```bash
   curl -f http://localhost:5000/api/health
   ```

2. **Review Server Logs**
   ```bash
   docker logs license-server --tail 100
   ```

3. **Database Issues**
   ```bash
   # Backup database
   docker exec license-server cp /app/data/licenses.db /app/data/licenses_backup.db
   
   # Check database integrity
   docker exec license-server sqlite3 /app/data/licenses.db "PRAGMA integrity_check;"
   ```

#### Emergency Access Grant

For critical situations, temporary bypass:

1. **Extend Fallback Expiry** (requires image rebuild)
2. **Create Emergency License** with extended validity
3. **Temporary License Server Bypass** (development only)

---

## 🔄 Automated Workflows

### License Lifecycle Management

#### Automated Renewal Reminders

```python
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

def send_renewal_reminder(user_email, user_id, days_left):
    msg = MIMEText(f"""
    Dear User,
    
    Your Dreamlet license ({user_id}) will expire in {days_left} days.
    Please contact your administrator for renewal.
    
    Best regards,
    Dreamlet Team
    """)
    
    msg['Subject'] = f'License Renewal Required - {days_left} days remaining'
    msg['From'] = 'admin@company.com'
    msg['To'] = user_email
    
    # Send email (configure SMTP settings)
    with smtplib.SMTP('smtp.company.com') as server:
        server.send_message(msg)

# Check for licenses expiring in 30, 14, and 7 days
for threshold in [30, 14, 7]:
    expiring = get_expiring_licenses(threshold)
    for license in expiring:
        send_renewal_reminder(
            license['email'], 
            license['user_id'], 
            threshold
        )
```

#### Auto-provisioning Integration

LDAP/Active Directory integration:

```python
import ldap
import requests

def sync_users_from_ldap():
    # Connect to LDAP
    conn = ldap.initialize('ldap://dc.company.com')
    conn.simple_bind_s('admin@company.com', 'password')
    
    # Search for users
    users = conn.search_s(
        'ou=users,dc=company,dc=com',
        ldap.SCOPE_SUBTREE,
        '(memberOf=cn=dreamlet-users,ou=groups,dc=company,dc=com)'
    )
    
    for user_dn, user_attrs in users:
        user_id = user_attrs['sAMAccountName'][0].decode()
        email = user_attrs['mail'][0].decode()
        
        # Check if license exists
        response = requests.get(
            f"{LICENSE_SERVER}/api/admin/licenses",
            headers={"X-API-Key": ADMIN_API_KEY}
        )
        
        existing_users = [u['user_id'] for u in response.json()['licenses']]
        
        if user_id not in existing_users:
            # Create new license
            requests.post(
                f"{LICENSE_SERVER}/api/admin/licenses",
                headers={"X-API-Key": ADMIN_API_KEY},
                json={
                    "user_id": user_id,
                    "email": email,
                    "company": "Company",
                    "days_valid": 365
                }
            )
            print(f"Created license for {user_id}")
```

---

## 📈 Reporting & Compliance

### Usage Reports

Monthly usage report:

```python
def generate_monthly_report(year, month):
    # Get all validation logs for the month
    response = requests.get(
        f"{LICENSE_SERVER}/api/admin/logs?limit=10000",
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    
    logs = response.json()['logs']
    
    # Filter by month
    monthly_logs = []
    for log in logs:
        log_date = datetime.fromisoformat(log['timestamp'])
        if log_date.year == year and log_date.month == month:
            monthly_logs.append(log)
    
    # Generate statistics
    unique_users = len(set(log['user_id'] for log in monthly_logs))
    total_validations = len(monthly_logs)
    successful_validations = len([l for l in monthly_logs if l['status'] == 'valid'])
    
    report = f"""
    Monthly Usage Report - {year}-{month:02d}
    ========================================
    
    Unique Active Users: {unique_users}
    Total Validations: {total_validations}
    Successful Validations: {successful_validations}
    Success Rate: {successful_validations/total_validations*100:.1f}%
    
    Top Users:
    """
    
    # User activity breakdown
    user_counts = {}
    for log in monthly_logs:
        user_id = log['user_id']
        user_counts[user_id] = user_counts.get(user_id, 0) + 1
    
    for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        report += f"    {user_id}: {count} validations\n"
    
    return report
```

### Compliance Auditing

```python
def audit_license_compliance():
    # Get all licenses
    response = requests.get(
        f"{LICENSE_SERVER}/api/admin/licenses",
        headers={"X-API-Key": ADMIN_API_KEY}
    )
    
    licenses = response.json()['licenses']
    
    audit_results = {
        'expired_active': [],
        'never_used': [],
        'suspicious_activity': []
    }
    
    for license in licenses:
        # Check for expired but active licenses
        expiry = datetime.fromisoformat(license['expiry_date'])
        if expiry < datetime.now() and license['is_active']:
            audit_results['expired_active'].append(license['user_id'])
        
        # Check for licenses never used
        if license['validation_count'] == 0:
            audit_results['never_used'].append(license['user_id'])
        
        # Check for suspicious validation patterns
        if license['validation_count'] > 1000:  # Threshold
            audit_results['suspicious_activity'].append(license['user_id'])
    
    return audit_results
```

---

## 🛡️ Security Best Practices

### License Server Security

1. **Network Security**
   - Use HTTPS in production
   - Firewall rules to limit access
   - VPN access for admin operations

2. **Authentication**
   - Rotate admin API keys regularly
   - Use strong, unique admin keys
   - Consider multi-factor authentication

3. **Database Security**
   - Regular backups
   - Encrypted storage
   - Access logging

4. **Monitoring**
   - Failed authentication attempts
   - Unusual validation patterns
   - System resource usage

### Client-Side Security

1. **License Key Protection**
   - Embedded in Docker image
   - Not stored in plain text
   - Hardware fingerprinting

2. **Communication Security**
   - TLS encryption for license validation
   - Certificate pinning (optional)
   - Timeout and retry logic

### Incident Response Plan

1. **Security Incident**
   - Immediate license revocation
   - Forensic log analysis
   - User notification process

2. **Service Disruption**
   - Failover procedures
   - Emergency communication
   - Service restoration priority

---

## 📞 Support Procedures

### User Support Workflow

1. **License Issues**
   - Verify license status
   - Check validation logs
   - Test license validation manually
   - Escalate to admin if needed

2. **Technical Issues**
   - Docker troubleshooting
   - Network connectivity tests
   - Application log analysis
   - Hardware requirement verification

### Administrator Escalation

Critical issues requiring immediate attention:
- License server outage
- Security breach detected
- Mass license validation failures
- Database corruption

Contact procedures:
- Primary admin notification
- Backup admin escalation
- Emergency contact list
- Incident documentation

---

## 🔧 Maintenance Tasks

### Regular Maintenance (Weekly)

```bash
# Check license server health
curl -f http://localhost:5000/api/health

# Review system statistics
curl -X GET http://localhost:5000/api/admin/stats \
  -H "X-API-Key: $ADMIN_API_KEY"

# Check for expiring licenses
# (Use monitoring script above)

# Backup database
docker exec license-server cp /app/data/licenses.db /app/data/backup_$(date +%Y%m%d).db
```

### Monthly Maintenance

```bash
# Clean old validation logs (optional)
# Analyze usage patterns
# Update license allocations
# Security audit
# Performance optimization
```

### Quarterly Review

- License utilization analysis
- Security policy review
- User access audit
- System capacity planning
- Disaster recovery testing

This comprehensive license management system ensures secure, auditable, and scalable access control for your Dreamlet Educational Video Production System deployment.