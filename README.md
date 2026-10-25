

ENG:
BXSW V4.0 v4.0 - Professional Web Reconnaissance Framework

A comprehensive, CLI-only security reconnaissance tool that runs on Windows, Linux, Termux, and Pydroid3 (Android). Every value printed comes from a live probe - no fake or placeholder data.

Features:
- 50+ reconnaissance modules including DNS, RDAP/WHOIS, Subdomain Enumeration, WAF/CDN Fingerprinting, Port Scanner, TLS/SSL Full Audit, HTTP Header Audit, HTTP Methods Tester, Redirect Chain Tracer, Technology Fingerprinting, Hidden Paths Scanner, robots.txt/sitemap.xml/security.txt parsers, Email Harvesting, IP Geolocation/ASN, Rate Limiting Test, and more.
- Two scan modes: [1] Website Scan (full recon of a domain/URL) and [2] IP Scanner (IP to domains + ports + URLs).
- Vulnerability Inventory: consolidated list of all findings with severity (Critical/High/Medium/Low), category, source module, location, and evidence.
- Cookies categorized: Secure/HttpOnly/SameSite analysis with session/persistent, third-party, CHIPS detection.
- Information Extraction: Full Link Extractor, Media/Video/Audio Extractor, Page Metadata (OG/Twitter/canonical), Contact Info (phones/social/addresses), Hidden Form Fields, Resource Inventory (JS/CSS/images/fonts), API Endpoint Discovery.
- Security Score Engine: A+ to F grade based only on measured checks.
- Full fallback: works without requests/dnspython (urllib + socket).
- Smart ANSI colors (isatty + NO_COLOR/FORCE_COLOR), clear() fallback for Android.
- --json-only: pure JSON on stdout, logs on stderr.
- --output: save full JSON report to file.
- --deep: extended path list. --quick: skip slow modules.
- ThreadPoolExecutor for concurrent scanning.
- Interactive target prompt when no argument given.
- Skull ASCII animation + banner on startup.

Requirements:
- Python 3.8+
- Optional: requests, dnspython, cryptography (full fallback without them)

Usage:
  python BXSW.py                          # interactive menu (Website Scan / IP Scanner)
  python BXSW.py example.com             # website scan
  python BXSW.py 8.8.8.8 --mode 2        # IP scanner
  python BXSW.py example.com --deep -o report.json
  python BXSW.py example.com --json-only > output.json
  python BXSW.py example.com --quick --threads 16

Modules (50+):
  DNS (A/AAAA/MX/NS/TXT/CNAME/SOA/CAA + PTR + AXFR) | RDAP/WHOIS | Subdomain Enum (crt.sh + DNS brute-force)
  WAF/CDN (27 fingerprints) | Port Scanner (57 ports + banners) | TLS/SSL (4 protocols + 6 ciphers + ALPN + HSTS preload)
  HTTP Headers (9 checks) | Cookies (rich parsing + categorization) | HTTP Methods (7) | Redirect Chain | Tech (51 fingerprints)
  Hidden Paths (26 + 22 deep) | robots.txt | sitemap.xml | security.txt | Email Harvesting | IP Geo/ASN | Rate Limiting
  Subdomain Takeover (15 services) | Open Redirect (30 params) | Host Header Injection (6) | Reflected Params (29)
  Mixed Content | Forms & CSRF | Favicon Hash (mmh3+SHA256) | Source Maps | Email Security (SPF/DMARC/MTA-STS/BIMI)
  Directory Listing | Secret/JWT Scanner (13 patterns) | GraphQL | WebSocket | Cache Poisoning | HPP | DNSSEC
  Vulnerability Inventory | Security Score (A+-F) | Full Link Extractor | Media Extractor | Metadata | Contact Info
  Hidden Fields | Resource Inventory | API Discovery | DNS Brute-Force | JS Endpoints | Cloud Buckets
  CORS Deep Testing | Sensitive Data Scanner | HTTP/2 Detection | Web Cache Deception

License: For authorized security testing and educational purposes only.
Author: BXSW V4.0 Development Team

<img src="https://github.com/wiliamdmax31/BSW-V4.0/blob/main/BSW-X2.png?raw=true"

FR:
BXSW V4.0 v4.0 - Framework Professionnel de Reconnaissance Web

Un outil de reconnaissance de securite complet, en ligne de commande uniquement, fonctionnant sur Windows, Linux, Termux et Pydroid3 (Android). Chaque valeur affichee provient d'une sonde en direct - aucune donnee fictive ou placeholder.

Fonctionnalites:
- 50+ modules de reconnaissance incluant DNS, RDAP/WHOIS, Enumeration de Sous-domaines, Fingerprinting WAF/CDN, Scanner de Ports, Audit TLS/SSL Complet, Audit des En-tetes HTTP, Testeur de Methodes HTTP, Traceur de Chaines de Redirection, Fingerprinting Technologique, Scanner de Chemins Caches, parseurs robots.txt/sitemap.xml/security.txt, Recolte d'Emails, Geolocalisation IP/ASN, Test de Limitation de Debit, et plus.
- Deux modes de scan: [1] Scan de Site Web (recon complete d'un domaine/URL) et [2] Scanner IP (IP vers domaines + ports + URLs).
- Inventaire des Vulnerabilites: liste consolidee de toutes les decouvertes avec severite (Critique/Eleve/Moyen/Faible), categorie, module source, emplacement et preuve.
- Cookies categorises: analyse Secure/HttpOnly/SameSite avec detection session/persistant, tiers, CHIPS.
- Extraction d'Informations: Extracteur de Liens Complets, Extracteur de Medias/Video/Audio, Metadonnees de Page (OG/Twitter/canonical), Infos de Contact (telephones/social/adresses), Champs Caches, Inventaire de Ressources (JS/CSS/images/fonts), Decouverte d'Endpoints API.
- Moteur de Score de Securite: note de A+ a F basee uniquement sur les verifications mesurees.
- Fallback complet: fonctionne sans requests/dnspython (urllib + socket).
- Couleurs ANSI intelligentes (isatty + NO_COLOR/FORCE_COLOR), fallback clear() pour Android.
- --json-only: JSON pur sur stdout, logs sur stderr.
- --output: sauvegarder le rapport JSON complet dans un fichier.
- --deep: liste de chemins etendue. --quick: ignorer les modules lents.
- ThreadPoolExecutor pour le scan concurrent.
- Invite interactive pour la cible si aucun argument n'est fourni.
- Animation ASCII skull + banniere au demarrage.

Prerequis:
- Python 3.8+
- Optionnel: requests, dnspython, cryptography (fallback complet sans eux)

Utilisation:
  python BXSW.py                          # menu interactif (Scan Site / Scanner IP)
  python BXSW.py example.com             # scan de site web
  python BXSW.py 8.8.8.8 --mode 2        # scanner IP
  python BXSW.py example.com --deep -o report.json
  python BXSW.py example.com --json-only > output.json
  python BXSW.py example.com --quick --threads 16

Modules (50+):
  DNS (A/AAAA/MX/NS/TXT/CNAME/SOA/CAA + PTR + AXFR) | RDAP/WHOIS | Enum Sous-domaines (crt.sh + brute-force DNS)
  WAF/CDN (27 empreintes) | Scanner de Ports (57 ports + bannieres) | TLS/SSL (4 protocoles + 6 suites + ALPN + HSTS preload)
  En-tetes HTTP (9 verifications) | Cookies (parsing riche + categorisation) | Methodes HTTP (7) | Chaine de Redirection | Tech (51 empreintes)
  Chemins Caches (26 + 22 deep) | robots.txt | sitemap.xml | security.txt | Recolte Emails | Geo IP/ASN | Limitation Debit
  Prise de Controle Sous-domaine (15 services) | Redirection Ouverte (30 params) | Injection En-tete Host (6) | Params Reflechis (29)
  Contenu Mixte | Formulaires & CSRF | Hash Favicon (mmh3+SHA256) | Source Maps | Securite Email (SPF/DMARC/MTA-STS/BIMI)
  Listing Repertoire | Scanner Secrets/JWT (13 patterns) | GraphQL | WebSocket | Empoisonnement Cache | HPP | DNSSEC
  Inventaire Vulnerabilites | Score de Securite (A+-F) | Extracteur Liens Complets | Extracteur Medias | Metadonnees | Infos Contact
  Champs Caches | Inventaire Ressources | Decouverte API | Brute-Force DNS | Endpoints JS | Buckets Cloud
  Test CORS Approfondi | Scanner Donnees Sensibles | Detection HTTP/2 | Tromperie Cache Web

Licence: Pour tests de securite autorises et usage educatif uniquement.
Auteur: Equipe de Developpement BXSW V4.0


Ar:
BXSW V4.0 v4.0 - إطار عمل احترافي لاستطلاع الويب

أداة استطلاع أمني شاملة، سطر أوامر فقط، تعمل على Windows و Linux و Termux و Pydroid3 (Android). كل قيمة مطبوعة تأتي من فحص حي (live probe) — لا بيانات وهمية أو placeholder.

الميزات:
- 50+ وحدة استطلاع تشمل: DNS، RDAP/WHOIS، تعداد النطاقات الفرعية، بصمات WAF/CDN، ماسح المنافذ، تدقيق TLS/SSL كامل، تدقيق رؤوس HTTP، اختبار طرق HTTP، تتبع سلاسل التحويل، بصمات التقنيات، ماسح المسارات المخفية، محللات robots.txt/sitemap.xml/security.txt، حصاد الإيميلات، تحديد الموقع/ASN، اختبار Rate Limiting، وأكثر.
- وضعان للمسح: [1] مسح موقع (استطلاع كامل لدومين/URL) و [2] ماسح IP (IP → domains + ports + URLs).
- قائمة تقييم الثغرات (Vulnerability Inventory): قائمة موحدة لجميع النتائج مع الخطورة (Critical/High/Medium/Low)، الفئة، الوحدة المصدر، المكان، والأدلة.
- Cookies مصنفة: تحليل Secure/HttpOnly/SameSite مع كشف session/persistent، third-party، CHIPS.
- استخراج المعلومات: مستخرج الروابط الكامل، مستخرج الوسائط/الفيديو/الصوت، بيانات الصفحة (OG/Twitter/canonical)، معلومات الاتصال (أرقام/شبكات اجتماعية/عناوين)، الحقول المخفية، جرد الموارد (JS/CSS/images/fonts)، اكتشاف API endpoints.
- محرك Security Score: تقييم من A+ إلى F مبني على فحوص فعلية فقط.
- Fallback كامل: يعمل بدون requests/dnspython (urllib + socket).
- تلوين ANSI ذكي (isatty + NO_COLOR/FORCE_COLOR)، fallback لـ clear() في Android.
- --json-only: JSON نقي على stdout، logs على stderr.
- --output: حفظ تقرير JSON كامل في ملف.
- --deep: قائمة مسارات موسعة. --quick: تخطي الوحدات البطيئة.
- ThreadPoolExecutor للمسح المتزامن.
- prompt تفاعلي للهدف إذا لم يُعطَ كـ argument.
- أنيميشن skull ASCII + banner عند البدء.

المتطلبات:
- Python 3.8+
- اختياري: requests, dnspython, cryptography (fallback كامل بدونها)

الاستخدام:
  python BXSW.py                          # قائمة تفاعلية (مسح موقع / ماسح IP)
  python BXSW.py example.com             # مسح موقع
  python BXSW.py 8.8.8.8 --mode 2        # ماسح IP
  python BXSW.py example.com --deep -o report.json
  python BXSW.py example.com --json-only > output.json
  python BXSW.py example.com --quick --threads 16

الوحدات (50+):
  DNS (A/AAAA/MX/NS/TXT/CNAME/SOA/CAA + PTR + AXFR) | RDAP/WHOIS | تعداد النطاقات الفرعية (crt.sh + DNS brute-force)
  WAF/CDN (27 بصمة) | ماسح المنافذ (57 منفذ + banners) | TLS/SSL (4 بروتوكولات + 6 cipher + ALPN + HSTS preload)
  رؤوس HTTP (9 فحوص) | Cookies (parsing غني + categorization) | طرق HTTP (7) | سلسلة تحويل | تقنيات (51 بصمة)
  مسارات مخفية (26 + 22 deep) | robots.txt | sitemap.xml | security.txt | حصاد إيميلات | Geo IP/ASN | Rate Limiting
  Subdomain Takeover (15 خدمة) | Open Redirect (30 params) | Host Header Injection (6) | Reflected Params (29)
  Mixed Content | Forms & CSRF | Favicon Hash (mmh3+SHA256) | Source Maps | Email Security (SPF/DMARC/MTA-STS/BIMI)
  Directory Listing | Secret/JWT Scanner (13 patterns) | GraphQL | WebSocket | Cache Poisoning | HPP | DNSSEC
  Vulnerability Inventory | Security Score (A+-F) | Full Link Extractor | Media Extractor | Metadata | Contact Info
  Hidden Fields | Resource Inventory | API Discovery | DNS Brute-Force | JS Endpoints | Cloud Buckets
  CORS Deep Testing | Sensitive Data Scanner | HTTP/2 Detection | Web Cache Deception

الترخيص: لاختبارات أمنية مُصرّح بها وأغراض تعليمية فقط.
المؤلف: فريق تطوير BXSW V4.0
