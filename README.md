
 # just Banner
 ![BXSW V4.0](https://pin.it/O0zimEZ9Z)
 
 ENG
# BXSW V4.0

All-in-one CLI web recon framework for Windows, Linux, Termux, Pydroid3. 100% live probes, no fake data.

## Modes
- [1] Website Scan - Full domain/URL recon, vuln inventory, security score
- [2] IP Scanner - Reverse IP, open ports, services, TLS certs, live URLs
- [3] Social Media OSINT - Public username/profile lookup across 25+ platforms

## Key Features
- 100+ live modules (DNS, RDAP, TLS, Ports, WAF, Headers, Cookies, Paths)
- Deep vuln checks (CORS, Open Redirect, SSRF, LFI, SQLi, XXE, GraphQL)
- Info extraction (links, JS, APIs, media, emails, metadata)
- Vulnerability Inventory + Confidence + Remediation
- Safe 100% shown if clean after deep probes
- Cookies categorization + rich parsing
- Stealth/Proxy/Delay/Threads
- Resume/Diff/Multi-target
- JSON/HTML reports, --json-only
- Works without requests/dnspython (fallback)

## Usage
```bash
python BXSW.py                    # interactive
python BXSW.py example.com        # website scan
python BXSW.py 8.8.8.8 --mode 2   # IP scan
python BXSW.py username --mode 3  # social media OSINT
python BXSW.py example.com -o report.json
```

## Notes
- For authorized testing only
- Public-only for Social Media OSINT
- TLS verify off by default, use --verify-tls if needed

FR
# BXSW V4.0

Framework CLI tout-en-un pour le recon web. Windows/Linux/Termux/Pydroid3. Probes live uniquement.

## Modes
- [1] Scan Site - Recon complet + inventaire vuln + score
- [2] Scan IP - Reverse IP, ports, services, TLS, URLs
- [3] Social Media OSINT - Recherche publique nom/utilisateur

## Fonctions clés
- 100+ modules live (DNS, RDAP, TLS, Ports, WAF, Headers, Cookies)
- Vuln (CORS, Redirect, SSRF, LFI, SQLi, XXE, GraphQL)
- Extraction (liens, JS, API, médias, emails)
- Inventaire + confiance + remédiation
- Safe 100% si aucun résultat
- Stealth/Proxy/Throttle
- JSON/HTML, --json-only
- Fallback urllib/socket

## Usage
```bash
python BXSW.py
python BXSW.py example.com
python BXSW.py 8.8.8.8 --mode 2
python BXSW.py username --mode 3
```




## Note
Usage uniquement pour tests autorisés. OSINT public uniquement.



AR
# BXSW V4.0

أداة CLI شاملة للاستطلاع الأمني. تعمل على Windows/Linux/Termux/Pydroid3. فحص حي فقط بدون بيانات وهمية.

## الأوضاع
- [1] مسح موقع - استطلاع كامل + قائمة ثغرات + تقييم أمني
- [2] مسح IP - عناوين مرتبطة + منافذ + خدمات + شهادات + روابط
- [3] OSINT وسائل التواصل - بحث عام عن اسم مستخدم عبر منصات متعددة

## أهم الميزات
- +100 وحدة فحص حي (DNS, RDAP, TLS, Ports, WAF, Headers, Cookies)
- فحص ثغرات (CORS, Open Redirect, SSRF, LFI, SQLi, XXE, GraphQL)
- استخراج شامل (روابط، JS، APIs، وسائط، إيميلات)
- جرد ثغرات + درجة ثقة + توصيات
- Safe 100% عند النظافة التامة
- تخفي/بروكسي/تحكم بالطلبات
- تقارير JSON/HTML
- يعمل بدون مكتبات إضافية

## الاستخدام
```bash
python BXSW.py
python BXSW.py example.com
python BXSW.py 8.8.8.8 --mode 2
python BXSW.py username --mode 3
```

## ملاحظات
للاختبار المصرح به فقط. الوضع الثالث للبحث العام فقط.
