# Security Checklist - OWASP IoT Top 10

## I1: Weak, Guessable, or Hardcoded Passwords

- [ ] Brak hardcoded credentials w kodzie
- [ ] Wymuszenie silnych haseł (min. 12 znaków, złożoność)
- [ ] Unikalne hasła dla każdego urządzenia/kamery
- [ ] Regularna rotacja haseł co 90 dni

## I2: Insecure Network Services

- [ ] Wszystkie serwisy nasłuchują tylko na niezbędnych portach
- [ ] Firewall rules ograniczające dostęp
- [ ] Brak niepotrzebnych serwisów (telnet, SSH na prod)
- [ ] Rate limiting na wszystkich API

## I3: Insecure Ecosystem Interfaces

- [ ] API chronione tokenami JWT z expiration
- [ ] Walidacja wszystkich inputs (sanitization)
- [ ] HTTPS/TLS dla wszystkich external interfaces
- [ ] CORS properly configured

## I4: Lack of Secure Update Mechanism

- [ ] Podpisane cyfrowo obrazy Docker
- [ ] Weryfikacja checksums przed deployment
- [ ] Rollback mechanism w razie błędu
- [ ] Update notifications dla admina

## I5: Use of Insecure or Outdated Components

- [ ] Regularne skanowanie CVE (Trivy, Grype)
- [ ] Automated dependency updates (Dependabot)
- [ ] Base images aktualizowane co miesiąc
- [ ] Vendor security bulletins monitoring

## I6: Insufficient Privacy Protection

- [ ] Dane osobowe (twarze) zaszyfrowane at rest
- [ ] GDPR compliance (right to be forgotten)
- [ ] Minimalizacja zbieranych danych
- [ ] Anonymizacja logów po 30 dniach

## I7: Insecure Data Transfer and Storage

- [ ] TLS 1.2+ dla wszystkich transmisji
- [ ] Szyfrowanie bazy danych (AES-256)
- [ ] Secure key management (HashiCorp Vault / SOPS)
- [ ] No sensitive data in logs

## I8: Lack of Device Management

- [ ] Inwentaryzacja wszystkich kamer/urządzeń
- [ ] Monitoring statusu urządzeń
- [ ] Automatyczne wyłączanie nieaktywnych
- [ ] Audit trail dla zmian konfiguracji

## I9: Insecure Default Settings

- [ ] Wymuszenie zmiany domyślnych haseł
- [ ] Secure by default configuration
- [ ] Principle of least privilege
- [ ] Dokumentacja secure deployment

## I10: Lack of Physical Hardening

- [ ] Instrukcje fizycznego zabezpieczenia kamer
- [ ] Tamper detection gdzie możliwe
- [ ] Secure disposal procedures
- [ ] Physical access logging
