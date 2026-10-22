
English: Recon-X v4.0 - Professional Web Reconnaissance Framework
A comprehensive, CLI-only security reconnaissance tool that runs on Windows, Linux, Termux, and Pydroid3 (Android). Every value printed comes from a live probe—no fake or placeholder data.

🌟 Features
50+ Reconnaissance Modules: DNS, RDAP/WHOIS, Subdomain Enumeration, WAF/CDN Fingerprinting, Port Scanner, TLS/SSL Full Audit, HTTP Header Audit, HTTP Methods Tester, Redirect Chain Tracer, Technology Fingerprinting, Hidden Paths Scanner, robots.txt/sitemap.xml/security.txt parsers, Email Harvesting, IP Geolocation/ASN, Rate Limiting Test, and more.

Two Scan Modes:

Website Scan: Full reconnaissance of a domain/URL.

IP Scanner: IP-to-domains + ports + URLs mapping.

Vulnerability Inventory: Consolidated list of all findings with severity level (Critical/High/Medium/Low), category, source module, location, and concrete evidence.

Advanced Cookie Analysis: Secure/HttpOnly/SameSite analysis with session/persistent, third-party, and CHIPS detection.

Information Extraction: Full Link Extractor, Media/Video/Audio Extractor, Page Metadata (OG/Twitter/canonical), Contact Info (phones/social/addresses), Hidden Form Fields, Resource Inventory (JS/CSS/images/fonts), and API Endpoint Discovery.

Security Score Engine: Dynamic grade assignment from A+ to F based solely on measured checks.

Full Fallback System: Fully operational without requests or dnspython using native urllib + socket.

Smart ANSI Colors: isatty + NO_COLOR/FORCE_COLOR support, with a specialized clear() fallback for Android/Termux.

Flexible CLI Flags:

--json-only: Pure JSON output on stdout, logs on stderr.

--output <file>: Save the full JSON report to a file.

--deep: Extended path list scanning.

--quick: Skip slow modules for faster execution.

--threads <num>: ThreadPoolExecutor for concurrent high-speed scanning.

Interactive Mode: Automatic interactive target prompt when no arguments are given.

Startup Aesthetic: Skull ASCII animation + startup banner.

⚙️ Requirements & Installation
Python: 3.8+

Optional Dependencies: requests, dnspython, cryptography (full fallback operational without them).

💻 Usage Examples
Bash
python reconx.py                        # Interactive menu (Website Scan / IP Scanner)
python reconx.py example.com            # Standard website scan
python reconx.py 8.8.8.8 --mode 2       # IP scanner mode
python reconx.py example.com --deep -o report.json
python reconx.py example.com --json-only > output.json
python reconx.py example.com --quick --threads 16
🧩 Modules Overview (50+)
Core & Network: DNS (A, AAAA, MX, NS, TXT, CNAME, SOA, CAA, PTR, AXFR), RDAP / WHOIS, Subdomain Enum (crt.sh + DNS brute-force).

Fingerprinting & Scanners: WAF/CDN (27 fingerprints), Port Scanner (57 ports + banners), Technology Detection (51 fingerprints), HTTP/2 Detection, Favicon Hash (mmh3 + SHA256).

Security Audits: TLS/SSL (4 protocols, 6 ciphers, ALPN, HSTS preload), HTTP Headers (9 checks), HTTP Methods (7), CORS Deep Testing, Web Cache Deception, Cache Poisoning, HPP, DNSSEC.

Web Recon & Content: Hidden Paths (26 + 22 deep), robots.txt, sitemap.xml, security.txt, Directory Listing, Source Maps, Cloud Buckets, API Discovery, JS Endpoints.

Vulnerabilities & Extraction: Subdomain Takeover (15 services), Open Redirect (30 params), Host Header Injection (6), Reflected Parameters (29), Mixed Content, Forms & CSRF, Secret/JWT Scanner (13 patterns), GraphQL, WebSocket, Sensitive Data Scanner, Email Security (SPF, DMARC, MTA-STS, BIMI), Email Harvesting, IP Geo/ASN, Rate Limiting.

Reporting & Scoring: Vulnerability Inventory, Security Score Engine (A+ to F), Full Link Extractor, Media Extractor, Metadata Parser, Contact Info Harvester, Hidden Fields, Resource Inventory.

License: For authorized security testing and educational purposes only.

Author: Recon-X Development Team


                     ____________________________________________________________________________________________________________________________________________________________________________________________________________________________________________


French: Recon-X v4.0 - Framework Professionnel de Reconnaissance Web
Un outil de reconnaissance de sécurité complet, en ligne de commande uniquement, fonctionnant sur Windows, Linux, Termux et Pydroid3 (Android). Chaque valeur affichée provient d'une sonde en direct — aucune donnée fictive ou placeholder.

🌟 Fonctionnalités
50+ modules de reconnaissance : DNS, RDAP/WHOIS, Énumération de Sous-domaines, Fingerprinting WAF/CDN, Scanner de Ports, Audit TLS/SSL Complet, Audit des En-têtes HTTP, Testeur de Méthodes HTTP, Traceur de Chaînes de Redirection, Fingerprinting Technologique, Scanner de Chemins Cachés, parseurs robots.txt/sitemap.xml/security.txt, Récolte d'Emails, Géolocalisation IP/ASN, Test de Limitation de Débit, et plus encore.

Deux modes de scan :

Scan de Site Web : Reconnaissance complète d'un domaine ou d'une URL.

Scanner IP : Conversion IP vers domaines + ports + URLs.

Inventaire des Vulnérabilités : Liste consolidée de toutes les découvertes avec niveau de sévérité (Critique/Élevé/Moyen/Faible), catégorie, module source, emplacement et preuve concrète.

Analyse Avancée des Cookies : Analyse Secure/HttpOnly/SameSite avec détection session/persistant, tiers et CHIPS.

Extraction d'Informations : Extracteur de Liens Complets, Extracteur de Médias (Vidéo/Audio), Métadonnées de Page (OG/Twitter/canonical), Infos de Contact (téléphones/réseaux sociaux/adresses), Champs Cachés, Inventaire de Ressources (JS/CSS/images/fonts) et Découverte d'Endpoints API.

Moteur de Score de Sécurité : Note de A+ à F attribuée uniquement sur la base de vérifications mesurées.

Fallback Complet : Fonctionne sans requests ni dnspython grâce à l'utilisation native de urllib + socket.

Couleurs ANSI Intelligentes : Support de isatty + NO_COLOR/FORCE_COLOR, avec fallback clear() pour Android.

Options CLI Flexibles : --json-only, --output <fichier>, --deep, --quick, --threads <nombre>.

Mode Interactif : Invite de cible interactive si aucun argument n'est fourni.

Esthétique au Démarrage : Animation ASCII d'une tête de mort (skull) + bannière.

⚙️ Prérequis
Python : 3.8+

Dépendances optionnelles : requests, dnspython, cryptography (fonctionnement complet en mode fallback sans elles).

💻 Utilisation
Bash
python reconx.py                        # Menu interactif (Scan Site / Scanner IP)
python reconx.py example.com            # Scan de site web standard
python reconx.py 8.8.8.8 --mode 2       # Scanner IP
python reconx.py example.com --deep -o report.json
python reconx.py example.com --json-only > output.json
python reconx.py example.com --quick --threads 16
🧩 Modules (50+)
DNS & Réseau : DNS (A, AAAA, MX, NS, TXT, CNAME, SOA, CAA, PTR, AXFR), RDAP/WHOIS, Enum Sous-domaines (crt.sh + force brute DNS).

Fingerprinting & Scanners : WAF/CDN (27 empreintes), Scanner de Ports (57 ports + bannières), Tech (51 empreintes), Détection HTTP/2, Hash Favicon (mmh3 + SHA256).

Audits de Sécurité : TLS/SSL (4 protocoles, 6 suites, ALPN, préchargement HSTS), En-têtes HTTP (9 vérifications), Méthodes HTTP (7), Test CORS approfondi, Tromperie Cache Web, Empoisonnement de Cache, HPP, DNSSEC.

Recon & Contenu Web : Chemins cachés (26 + 22 deep), robots.txt, sitemap.xml, security.txt, Listing de Répertoire, Source Maps, Buckets Cloud, Découverte API, Endpoints JS.

Vulnérabilités & Extraction : Prise de contrôle de sous-domaine (15 services), Redirection ouverte (30 paramètres), Injection d'en-tête Host (6), Paramètres réféchis (29), Contenu mixte, Formulaires & CSRF, Scanner Secret/JWT (13 motifs), GraphQL, WebSocket, Scanner de données sensibles, Sécurité Email (SPF, DMARC, MTA-STS, BIMI), Récolte Emails, Géo IP/ASN, Rate Limiting.

Rapports & Score : Inventaire des vulnérabilités, Score de Sécurité (A+-F), Extracteur de liens, Extracteur de médias, Métadonnées, Infos de contact, Champs cachés, Inventaire des ressources.

Licence : Pour tests de sécurité autorisés et usage éducatif uniquement.

Auteur : Équipe de Développement Recon-X


                     ____________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

                     
Arabic: Recon-X v4.0 - إطار عمل احترافي لاستطلاع الويب
أداة استطلاع أمني شاملة تعمل حصرياً عبر سطر الأوامر (CLI) وتتوافق مع أنظمة Windows، Linux، Termux، و Pydroid3 (Android). كل قيمة مطبوعة تأتي من فحص حي (Live Probe) — خالية تماماً من البيانات الوهمية أو القيم المؤقتة (Placeholders).

🌟 الميزات الأساسية
50+ وحدة استطلاع تشمل: DNS، RDAP/WHOIS، تعداد النطاقات الفرعية، بصمات WAF/CDN، ماسح المنافذ، تدقيق TLS/SSL شامل، تدقيق رؤوس HTTP، اختبار طرق HTTP، تتبع سلاسل التحويل، بصمات التقنيات، ماسح المسارات المخفية، محللات robots.txt/sitemap.xml/security.txt، حصاد الإيميلات، تحديد الموقع الجغرافي/ASN، اختبار حدود المعدل (Rate Limiting)، والمزيد.

وضعان للمسح:

مسح موقع (Website Scan): استطلاع كامل لدومين أو رابط محدد.

ماسح IP (IP Scanner): تحويل الـ IP إلى نطاقات مرتبطة + منافذ + روابط.

قائمة تقييم الثغرات (Vulnerability Inventory): قائمة موحدة لجميع الاكتشافات مصنفة حسب مستوى الخطورة (Critical/High/Medium/Low)، والفئة، والوحدة المصدر، والموقع، والأدلة الفعلية.

تحليل متقدم لـ Cookies: تحليل إعدادات Secure/HttpOnly/SameSite مع كشف الجلسات (session/persistent)، والجهات الخارجية (third-party)، وتقنية CHIPS.

استخراج المعلومات: مستخرج الروابط الكامل، مستخرج الوسائط (فيديو/صوت)، بيانات الصفحة التعريفية (OG/Twitter/canonical)، معلومات الاتصال (أرقام الهواتف/شبكات التواصل/العناوين)، الحقول المخفية، جرد الموارد (JS/CSS/images/fonts)، واكتشاف نقاط نهايات الـ API.

محرك تقييم الأمان (Security Score Engine): منح تقييم يتراوح من A+ إلى F استناداً حصراً إلى الفحوصات الفعلية المقاسة.

نظام استبدال متكامل (Full Fallback): يعمل بكفاءة تامة حتى بدون مكتبات requests أو dnspython بالاعتماد على ميزات urllib + socket الأساسية في بايثون.

تلوين ANSI ذكي: دعم تلقائي لخاصية isatty مع متغيرات NO_COLOR/FORCE_COLOR، بالإضافة إلى معالجة خاصة لمرونة دالة clear() على نظام Android.

خيارات سطر أووامر مرنة (CLI Flags):

--json-only: إخراج بيانات JSON نقية على الـ stdout مع توجيه السجلات للـ stderr.

--output <file>: حفظ تقرير JSON الشامل في ملف نصي.

--deep: تفعيل قائمة مسارات موسعة.

--quick: تخطي الوحدات البطيئة لتسريع الفحص.

--threads <num>: استخدام ThreadPoolExecutor للفحص المتزامن السريع.

وضع تفاعلي (Interactive Prompt): نافذة تفاعلية لإدخال الهدف تلقائياً في حال لم يتم تمرير أي وسائط (arguments).

تصميم عند البدء: رسوم متحركة جمجمة بتقنية ASCII + بانر ترحيبي.

⚙️ المتطلبات الأساسية
Python: إصدار 3.8 أو أحدث.

مكتبات اختياريّة: requests, dnspython, cryptography (تعمل الأداة بكامل وظائفها بنظام البديل التلقائي بدونها).

💻 أوامر الاستخدام
Bash
python reconx.py                        # القائمة التفاعلية (مسح موقع / ماسح IP)
python reconx.py example.com            # مسح موقع إلكتروني قياسي
python reconx.py 8.8.8.8 --mode 2       # وضع ماسح الـ IP
python reconx.py example.com --deep -o report.json
python reconx.py example.com --json-only > output.json
python reconx.py example.com --quick --threads 16
🧩 نظرة عامة على الوحدات (50+)
الشبكات ونطاقات DNS: DNS (A, AAAA, MX, NS, TXT, CNAME, SOA, CAA, PTR, AXFR)، RDAP / WHOIS، تعداد النطاقات الفرعية (crt.sh + Brute-force DNS).

البصمات والمسح الشامل: WAF/CDN (27 بصمة)، ماسح المنافذ (57 منفذاً مع البانرات)، اكتشاف التقنيات (51 بصمة)، كشف بروتوكول HTTP/2، حساب تجزئة الأيقونة Favicon (mmh3 + SHA256).

التدقيقات الأمنية: TLS/SSL (4 بروتوكولات، 6 خوارزميات تشفير، ALPN، وتحميل HSTS مسبقاً)، رؤوس HTTP (9 فحوصات)، طرق HTTP (7)، اختبارات CORS المتقدمة، خداع التخزين المؤقت (Web Cache Deception)، التسميم المؤقت، HPP، و DNSSEC.

الاستطلاع واستخراج المحتوى: المسارات المخفية (26 + 22 موسعة)، robots.txt، sitemap.xml، security.txt، استعراض المجلدات (Directory Listing)، خرائط المصادر (Source Maps)، حاويات السحابة (Cloud Buckets)، اكتشاف الـ API، ونقاط نهايات JavaScript.

الثغرات واستخراج البيانات: الاستحواذ على النطاقات الفرعية (15 خدمة)، إعادة التوجيه المفتوحة (30 متغيراً)، حقن رأس المضيف (Host Header Injection)، المتغيرات المنعکسة (Reflected Params)، المحتوى المختلط، النماذج وحماية CSRF، ماسح الأسرار/JWT (13 نمطاً)، GraphQL، WebSocket، ماسح البيانات الحساسة، أمان البريد الإلكتروني (SPF, DMARC, MTA-STS, BIMI)، حصاد الإيميلات، تحديد الموقع/ASN، واختبار Rate Limiting.

التقارير والتقييم: قائمة جرد الثغرات، محرك تقييم الأمان (A+ إلى F)، مستخرج الروابط الشامل، مستخرج الوسائط، محلل البيانات التعريفية، جامع معلومات الاتصال، الحقول المخفية، وجرد الموارد.

الترخيص: مخصص لاختبارات الأمان المصرح بها والأغراض التعليمية فقط.

المؤلف: فريق تطوير Recon-X






