# RAPPORT D'AUDIT INDÉPENDANT — FLASHBACK RESTORE
**Auditeur :** Senior Security & Architecture Auditor
**Date :** Juin 2025
**Statut produit :** Pre-launch (HTTP Basic Auth)
**Périmètre :** Backend, Frontend, Infrastructure, Sécurité, DevOps

---

> **AVERTISSEMENT PRÉLIMINAIRE**
> Ce produit, en l'état actuel, **ne doit pas être mis en production publique**. La surface d'attaque est critique, les secrets sont compromis, l'isolation des services est inexistante, et plusieurs flux métier sont fonctionnellement cassés. Un lancement dans ces conditions exposerait les données utilisateurs, les credentials de production et la viabilité financière du projet à des risques immédiats et concrets.

---

## 1. SÉCURITÉ — 1.5/10

### Diagnostic général
L'architecture de sécurité est inexistante. Il ne s'agit pas de lacunes ponctuelles corrigeables à la marge : c'est un échec systémique de conception sécurisée à chaque couche de la stack.

### Secrets & Credentials
- **Clé Gemini API commitée dans git** (`.env.example`). La rotation est obligatoire maintenant, pas après lecture de ce rapport. Toute personne ayant eu accès au dépôt possède cette clé.
- **`.env` en permissions 644** sur le VPS. Lisible par tout utilisateur du système. Sur un environnement partagé ou compromis, c'est une exfiltration immédiate de l'intégralité des secrets.
- **`.env.bak` non gitignorés**. Les backups de fichiers secrets sont aussi dangereux que les originaux.
- **`config.py.bak` exposé** dans le repo ou le filesystem. Le code source de configuration ne doit jamais avoir de backup en clair.
- **Credentials DB triviaux** (vraisemblablement `postgres/postgres` ou équivalent). Sur un port 5432 exposé publiquement, c'est une invitation explicite.
- **Secrets hardcodés dans les unit files systemd**. Ces fichiers sont souvent loggués, parfois dans journald, parfois dans des outils de monitoring tiers. Vecteur d'exfiltration silencieux.
- **Clé D-ID encodée en base64 `email:password`**. Ce n'est pas du chiffrement. C'est de la fausse sécurité qui donne une illusion de protection.
- **Secrets n8n en dur** (encryption key, license key). Si n8n est compromis, toute automatisation backend est compromise.
- **Webhook Stripe sans vérification de signature**. N'importe qui peut forger un événement `payment_intent.succeeded` et obtenir des crédits gratuits ou déclencher des actions arbitraires côté métier.

### Exposition réseau
- **Ports 8000 et 8001 ouverts sur Internet**. Traefik est censé être le seul point d'entrée, mais le backend FastAPI et le frontend Next.js sont directement accessibles en bypassant l'intégralité de l'authentification, du rate limiting et des headers de sécurité. L'HTTP Basic Auth pre-launch ne protège rien.
- **Port 5432 PostgreSQL exposé publiquement**. Une base de données de production ne doit jamais être joignable depuis Internet. Jamais. Couplé aux credentials triviaux, c'est un accès direct en lecture/écriture à toutes les données utilisateurs.
- **Ports superflus exposés** (5678 n8n, 3001, 4000, 11434 Ollama, 5001-5002). Chaque port ouvert est une surface d'attaque. Ces services n'ont aucune raison d'être accessibles depuis l'extérieur.
- **Docker socket exposé à Traefik**. Compromission de Traefik = escalade immédiate vers root sur l'hôte via le socket Docker.

### TLS & Headers
- **TLS 1.0 et 1.1 actifs**. Ces protocoles sont officiellement dépréciés depuis RFC 8996 (2021). POODLE, BEAST, et autres attaques connues s'appliquent.
- **Zéro headers de sécurité sur HTTPS**. Les headers (`Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`) sont potentiellement présents sur HTTP direct mais absents via Traefik HTTPS. Inutilité complète : personne n'accède en HTTP direct en production.
- **CORS `allow_methods=*` et `allow_headers=*`**. Aucune restriction. Toute origine, toute méthode, tout header.
- **`/docs` FastAPI public**. La documentation Swagger expose l'intégralité du schéma API, les paramètres, les types de retour. Guide de reconnaissance gratuit pour un attaquant.

### Auth & Sessions
- **SSRF non authentifié sur `/api/animate/{job_id}`**. Un endpoint qui effectue des requêtes vers des URLs externes sans authentification est un vecteur SSRF classique exploitable pour atteindre les services internes (metadata AWS/cloud, services locaux).
- **Endpoints Stripe sans JWT**. Les webhooks de paiement doivent être protégés par signature Stripe ET potentiellement par IP allowlist. Ni l'un ni l'autre n'est en place.
- **JWT sans révocation**. Un token volé reste valide jusqu'à expiration. Pas de blacklist, pas de rotation forcée possible.
- **Tokens de reset de mot de passe stockés en clair**. Si la base est compromise, tous les tokens de reset actifs permettent une prise de contrôle immédiate de tous les comptes ayant initié un reset.
- **Rate limiter bypass via `X-Forwarded-For`**. Un attaquant peut forger ce header pour contourner le rate limiting IP. Trivial à exploiter.
- **Rate limiter mémoire non partagé entre workers**. Avec plusieurs workers Uvicorn/Gunicorn, chaque worker maintient son propre compteur. Le rate limiting effectif est divisé par le nombre de workers.
- **Décorateurs rate limit factices**. Des décorateurs qui ne font rien donnent une fausse impression de protection dans le code. Plus dangereux que l'absence de décorateurs car ils masquent le problème.

### Isolation
- **Services systemd en root sans aucune isolation** (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem`, `User=` non configurés). Un exploit applicatif dans FastAPI ou Next.js donne immédiatement un shell root sur l'hôte.
- **Pas de réseau Docker isolé** visible. Les containers peuvent communiquer librement entre eux.

**Score : 1.5/10** — Aucun des fondamentaux n'est en place. La totalité des vecteurs d'attaque classiques sont exploitables.

---

## 2. CODE & ARCHITECTURE — 3/10

### Async/Sync
- **`nest_asyncio` appliqué globalement**. Patcher la boucle événementielle asyncio en production est un anti-pattern majeur masquant des problèmes de conception. Il cache vraisemblablement des appels synchrones bloquants dans des contextes async.
- **Envoi d'emails synchrone dans des routes async**. Chaque envoi d'email bloque le thread event loop de FastAPI. Sous charge, cela paralyse le serveur. La route répond en N secondes (latence SMTP) au lieu de millisecondes.

### Gestion des erreurs
- **Fuite d'erreurs brutes vers le client**. Les stack traces Python, les messages d'erreur SQLAlchemy avec noms de tables/colonnes, les détails d'exception Stripe sont renvoyés tels quels. Double problème : information disclosure pour l'attaquant, expérience utilisateur catastrophique.
- **Email send silencieux sur échec**. Un email de confirmation ou de reset qui échoue sans log ni exception propagée signifie que des utilisateurs ne reçoivent jamais leurs emails sans que le système le sache.
- **`champ analyse=None type:ignore`**. Les `type: ignore` sont des dettes techniques explicites. Celui-ci cache probablement un bug de None check manquant qui plantera en production sur certains inputs.

### Pool & Connexions DB
- **Double pool de connexions DB**. Deux pools actifs simultanément multiplient les connexions inutilement et peuvent provoquer des épuisements de pool sous charge.
- **Init DB confuse**. Si l'initialisation de la base peut être appelée plusieurs fois ou depuis plusieurs endroits, le risque de race condition ou de migration partielle est réel.

### Métier
- **`/api/analyze` consomme l'upload sans vérifier les crédits**. L'image est traitée, des ressources sont consommées (stockage, CPU, potentiellement API Gemini), et seulement ensuite on vérifie si l'utilisateur a des crédits. Un utilisateur sans crédits peut faire traiter des images gratuitement à répétition. Bug métier et financier direct.
- **`cleanup` tente `os.remove()` sur des URLs distantes**. `os.remove("https://...")` lèvera une exception. Le cleanup ne fonctionne pas pour les fichiers sur stockage distant. Accumulation silencieuse de fichiers.
- **`_vers_url` incorrecte pour URLs externes**. La fonction de conversion de chemin vers URL produit des URLs invalides pour les ressources distantes. Les animations/résultats sont potentiellement inaccessibles.
- **Cache plan sans invalidation**. Un plan mis en cache peut être servi après changement de configuration (prix, fonctionnalités, quotas). Des utilisateurs peuvent recevoir des informations tarifaires obsolètes ou accéder à des fonctionnalités qui ne leur sont plus accordées.
- **Contrainte CHECK qui exclut "colorisation"**. Le type d'opération "colorisation" est rejeté par la base de données si cette feature existe ou est prévue. Crash en production garanti à la première utilisation.
- **Validation MIME par Content-Type client**. Le navigateur peut mentir. Un fichier malveillant renommé en `.jpg` passe la validation. Il faut lire les magic bytes.

### Patterns
- **`register` avec valeurs hardcodées**. Les valeurs par défaut hardcodées dans la fonction d'inscription (plan, crédits initiaux, etc.) sont un risque de dérive : changer le modèle commercial nécessite de retrouver et modifier le code, pas la configuration.
- **`load_dotenv` source confuse**. Si la source du `.env` chargé n'est pas déterministe, le comportement en production vs développement peut diverger silencieusement.

**Score : 3/10** — Des bugs métier actifs, des anti-patterns critiques en async, une gestion d'erreurs quasi-absente.

---

## 3. MODÈLE DE DONNÉES — 4/10

### Schéma & Contraintes
- **Contrainte CHECK excluant "colorisation"**. Voir Code & Architecture. Si le type de job inclut la colorisation comme feature, la contrainte doit être mise à jour. Si elle ne doit pas l'inclure, le code doit le savoir. État actuel : incohérence silencieuse.
- **Tokens de reset en clair dans la table `reinitialisation_mdp`**. Ces tokens doivent être hashés (bcrypt ou SHA-256 suffisent). En l'état, dump de la table = accès à tous les comptes ayant un reset en cours.
- **5 nouvelles colonnes ajoutées par migration récente** sans visibilité sur leur usage effectif dans le code. `retention_jours` : est-ce un TTL appliqué par un job ? Par qui ? `chemin_animation` : doublon potentiel avec le champ dans `travaux` ? `taille_original/taille_resultat` : peuplées comment, par qui, lors de quel event ?

### Indexes
- Aucun index mentionné sur les colonnes de recherche fréquente : `utilisateurs.email` (lookup auth à chaque requête), `travaux.utilisateur_id` (listing des jobs), `consommation_credits.utilisateur_id` (calcul du solde), `audit_logs.utilisateur_id` + `audit_logs.created_at` (requêtes admin).
- Sur PostgreSQL, une table `audit_logs` sans index partiel sur `created_at` sera inutilisable en production dès quelques millions de lignes.

### Types & Cohérence
- **`derniere_activite`** : timezone-aware ou naive ? PostgreSQL avec `TIMESTAMP WITHOUT TIME ZONE` provoque des bugs subtils sur les comparaisons temporelles entre sessions utilisateurs de fuseaux horaires différents.
- **7 tables + colonnes migrées récemment** : la migration a-t-elle inclus des valeurs par défaut pour les lignes existantes ? Des colonnes `NOT NULL` sans défaut sur des tables peuplées provoquent des erreurs de migration en production.
- **Pas de mention de soft delete**. La suppression de compte (RGPD) avec `os.remove()` en cascade non fonctionnelle (cf. Code) signifie que les fichiers physiques ne sont jamais supprimés.
- **`audit_logs`** : si cette table existe, son usage doit être systématique sur toutes les mutations sensibles. Un audit log incomplet est trompeur.

### Volumétrie
- **Pas de pagination sur la suppression totale**. Un utilisateur avec 10 000 jobs qui supprime son compte déclenche une requête `DELETE` sans LIMIT. Timeout garanti, locks de table, indisponibilité partielle.

**Score : 4/10** — Le schéma de base est cohérent mais les manques en indexation, la contrainte CHECK incohérente et les tokens en clair sont des problèmes concrets.

---

## 4. GESTION ADMIN — 2.5/10

### Dashboard & Monitoring
- **Aucun dashboard d'administration mentionné**. Comment un opérateur surveille-t-il les jobs en cours, les échecs d'API Gemini, les erreurs de paiement, l'utilisation des crédits ? En se connectant directement à la base ?
- **Health endpoint bavard**. Un endpoint `/health` qui expose les versions, les statuts de connexions internes, les métriques de pool DB est un guide de reconnaissance. Il doit répondre `200 OK` ou `503` uniquement, sans détails.
- **Logs** : aucun système de log centralisé mentionné (Loki, ELK, CloudWatch). Les logs systemd (`journald`) ne sont pas suffisants en production : rotation, recherche, alerting.

### Droits & Isolation
- **Services en root**. L'opérateur n'a aucun moyen de distinguer les actions du service des actions d'administration. Tout est root. L'audit trail système est inutilisable.
- **Pas de séparation des rôles** visible. Le même compte applicatif accède à toutes les tables. Un principe de moindre privilège imposerait des rôles DB distincts (read-only pour l'analytics, write limité pour l'application).

### Cleanup & Rétention
- **`cleanup` non fonctionnel pour les fichiers distants** (cf. Code). Les fichiers s'accumulent sans limite.
- **`retention_jours`** nouvellement ajouté mais aucun job de cleanup visible qui l'utilise. La colonne existe, la donnée est stockée, mais rien ne l'applique.
- **58 fichiers dans `uploads/`** lisibles en 644. Ces fichiers sont-ils des photos personnelles d'utilisateurs ? Si oui, c'est une violation RGPD active : toute personne accédant au serveur lit les photos des utilisateurs.

### Audit Trail
- **`audit_logs` existe** mais sans garantie d'exhaustivité. Les mutations critiques (changement de plan, consommation de crédits, reset de mot de passe, suppression de compte) doivent toutes être auditées. Sans review du code, l'exhaustivité est douteuse.

**Score : 2.5/10** — Pas d'outillage opérationnel réel. L'opérateur est aveugle sur l'état de son système.

---

## 5. UX & FRONTEND — 3.5/10

### Flux de conversion (critique métier)
- **Boutons "S'abonner" inopérants**. Le flux de conversion principal — la raison d'être d'un SaaS — est cassé. Un utilisateur qui voudrait payer ne peut pas. C'est un revenu nul garanti tant que ce bug existe.
- **Toggle Connexion/Inscription cassé**. Le premier point de contact avec l'utilisateur est défaillant. L'onboarding est impossible sans manipulation manuelle de l'URL.
- **Validation formulaire auth inexistante**. Un utilisateur peut soumettre un formulaire avec un email invalide ou un mot de passe vide. Le comportement résultant (erreur serveur brute ?) est imprévisible.

### Erreurs console
- **`AuthError` sur 100% des pages**. Toute personne ouvrant les DevTools voit des erreurs. Cela signale une configuration NextAuth mal initialisée, probablement une session non trouvée traitée comme une erreur plutôt qu'un état normal. Impact SEO potentiel si les crawlers interprètent les erreurs JS.

### Navigation & Cohérence
- **Liens réseaux sociaux pointant sur `#`**. Ce sont des dead links qui signalent un produit inachevé.
- **Mentions légales = doublon `/terms`**. Deux URLs pour le même contenu sans canonical = duplicate content SEO.
- **URLs navbar vs footer incohérentes**. Deux menus de navigation avec des URLs différentes pour les mêmes destinations : l'un fonctionne, l'autre non, ou ils pointent vers des pages différentes.
- **Pas de navbar/footer sur pages auth et 404**. Un utilisateur sur la page 404 ou en cours d'inscription est piégé sans navigation de secours.

### SEO
- **Titre de page identique partout**. Google indexe toutes les pages avec le même titre. Catastrophique pour le référencement différencié.
- **`robots.txt` et `sitemap.xml` absents**. Les crawlers indexent ce qu'ils veulent, y compris des pages auth ou des pages en construction.
- **H1 manquants ou mal formés sur 5 pages**. Structure sémantique défaillante.

### Accessibilité
- **Inputs sans labels visibles**. Non-conformité WCAG 2.1 AA. Lecteurs d'écran inutilisables. Problème légal potentiel selon juridiction.
- **FAQ non fonctionnelle**. Les accordéons ne s'ouvrent pas. Une section entière du site est inutilisable.

### Contenu
- **`"0€à vie"`** sans espace. **`"FlashbackRestore"`** sans espace. **`"0 animation"`** grammaticalement incorrect. Ces fautes signalent un manque de QA basique et nuisent à la crédibilité.
- **Emails de contact `.fr` vs `.com` incohérents**. Lequel est valide ? Les utilisateurs qui contactent le `.fr` si c'est le `.com` qui est actif n'obtiennent jamais de réponse.
- **Images before/after en double**. Duplication de contenu visuel sans raison apparente.

**Score : 3.5/10** — Le flux de conversion est cassé. La navigation est incohérente. Le SEO est inexistant. L'accessibilité est défaillante.

---

## 6. BONNES PRATIQUES — 2/10

### Git & Secrets
- **Clé API commitée dans l'historique git**. Le `git log` contient la compromission. Un `git filter-branch` ou `git filter-repo` est nécessaire, suivi d'une rotation obligatoire de la clé.
- **`.env.bak`, `config.py.bak` non gitignorés**. Le `.gitignore` ne couvre pas les fichiers de backup. Standard minimal non respecté.
- **`.env.example` avec vraies valeurs**. Ce fichier est censé contenir des valeurs d'exemple fictives, pas les vraies clés de production.

### CI/CD
- **Aucun pipeline CI/CD mentionné**. Les déploiements sont vraisemblablement manuels (SSH + restart systemd). Pas de tests automatisés avant déploiement, pas de rollback automatique, pas de validation de la configuration.
- **`npx` sans version figée**. `npx some-tool` résout la version au moment de l'exécution. Un outil qui publie une version malveillante est exécuté automatiquement au prochain déploiement (supply chain attack).

### Tests
- **Test unitaire incohérent** (mentionné dans les bugs P1). Un test qui ne teste pas ce qu'il prétend tester donne une fausse confiance. Pire que l'absence de test.
- **Aucune mention de tests d'intégration, de tests E2E, de tests de charge**. Pour un SaaS de traitement d'images avec API externes, les tests d'intégration sont critiques.

### Documentation
- **Chemin `.env` non documenté**. Un nouveau développeur ou un opérateur ne sait pas où trouver le fichier de configuration.
- **Architecture non documentée**. La stack est complexe (FastAPI + Next.js + PostgreSQL + Redis + Traefik + Stripe + Gemini + D-ID + n8n). Sans documentation d'architecture, la maintenance est impossible à déléguer.

### Politique de sécurité
- **Pas de politique de mot de passe**. Longueur minimale, complexité, pas de validation côté serveur visible.
- **Pas de rotation des secrets planifiée**.
- **`/docs` Swagger public en production**. À désactiver avec `docs_url=None` dans FastAPI hors développement.
- **Docker compose backups avec secrets**. Les fichiers `docker-compose.yml` de backup contiennent des secrets et ne sont pas dans `.gitignore`.

**Score : 2/10** — Pas de CI/CD, secrets compromis dans git, aucune politique de sécurité formalisée, tests insuffisants ou incorrects.

---

## NOTE GLOBALE — 2.5/10

| Axe | Note |
|-----|------|
| Sécurité | 1.5/10 |
| Code & Architecture | 3/10 |
| Modèle de données | 4/10 |
| Gestion Admin | 2.5/10 |
| UX & Frontend | 3.5/10 |
| Bonnes Pratiques | 2/10 |
| **GLOBAL** | **2.5/10** |

> Ce score n'est pas un jugement sur l'ambition du projet. Il reflète l'état objectif d'un produit qui accumule des risques critiques non adressés à travers toutes ses couches. La base fonctionnelle semble exister — des fonctionnalités sont implémentées, un modèle de données existe, une stack cohérente est choisie. Mais la dette technique et sécuritaire est si profonde qu'un lancement en l'état créerait des risques légaux (RGPD), financiers (Stripe fraud), et de réputation immédiats.

---

## TOP 10 ACTIONS PRIORITAIRES (P0 — À TRAITER AVANT TOUT LE RESTE)

### #1 — ROTATION IMMÉDIATE DE TOUS LES SECRETS COMPROMIS
**Pourquoi maintenant :** La clé Gemini est dans l'historique git. Chaque seconde, elle peut être utilisée frauduleusement à vos frais.
**Actions :**
```
1. Révoquer immédiatement : clé Gemini, clés Stripe (test ET prod), 
   credentials D-ID, clé n8n, tout secret dans .env.bak/config.py.bak
2. Générer de nouveaux secrets
3. git filter-repo --path .env.example --invert-paths (purger l'historique)
4. Force-push + rotation des tokens d'accès GitHub/GitLab
5. Informer tous les collaborateurs ayant cloné le repo
```

### #2 — FERMER LES PORTS EXPOSÉS (8000, 8001, 5432)
**Pourquoi maintenant :** La base de données est accessible depuis Internet avec des credentials triviaux. C'est un accès direct à toutes les données utilisateurs.
```bash
# UFW — bloquer immédiatement
ufw deny 5432
ufw deny 8000  
ufw deny 8001
ufw deny 5678
ufw deny 3001
ufw deny 4000
ufw deny 11434
# Autoriser uniquement ce qui est nécessaire via Traefik (80, 443)
```

### #3 — CORRIGER LE WEBHOOK STRIPE (vérification de signature)
**Pourquoi maintenant :** N'importe qui peut envoyer un POST forgé et obtenir des crédits gratuits ou déclencher des opérations de facturation.
```python
# Remplacer la logique actuelle par :
import stripe
def verify_stripe_webhook(payload: bytes, sig_header: str) -> stripe.Event:
    try:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
```

### #4 — SÉCURISER LES FICHIERS SECRETS ET UPLOADS
```bash
# Permissions immédiates
chmod 600 /path/to/.env
chmod 600 /path/to/.env.bak  # puis supprimer
chmod 700 /path/to/uploads/
# Si uploads/ contient des photos utilisateurs : audit RGPD requis
# Créer utilisateur dédié pour chaque service
useradd -r -s /bin/false flashback-api
useradd -r -s /bin/false flashback-web
```

### #5 — AJOUTER AUTH SUR `/api/animate/{job_id}` ET ENDPOINTS STRIPE
**Pourquoi maintenant :** SSRF non authentifié = accès aux services internes du VPS depuis Internet.
```python
# FastAPI — dépendance obligatoire
@router.post("/api/animate/{job_id}")
async def animate(
    job_id: int,
    current_user: User = Depends(get_current_user)  # MANQUANT
):
    # Valider que job_id appartient à current_user
    # Valider que l'URL cible est dans une whitelist
```

### #6 — DÉSACTIVER TLS 1.0/1.1 ET ACTIVER LES HEADERS DE SÉCURITÉ VIA TRAEFIK
```yaml
# traefik.yml
tls:
  options:
    default:
      minVersion: VersionTLS12
      cipherSuites:
        - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
        - TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305

# Middleware headers
http:
  middlewares:
    security-headers:
      headers:
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        contentTypeNosniff: true
        frameDeny: true
        contentSecurityPolicy: "default-src 'self'"
        referrerPolicy: "strict-origin-when-cross-origin"
```

### #7 — CORRIGER LE FLUX DE CONVERSION (boutons S'abonner)
**Pourquoi maintenant :** Zéro revenu possible tant que ce flux est cassé. C'est la priorité métier absolue.
- Identifier pourquoi les handlers Stripe Checkout ne sont pas appelés
- Vérifier la configuration `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- Tester le flux complet en mode Stripe test avec logs activés
- Vérifier que les price IDs correspondent aux produits Stripe configurés

### #8 — ISOLER LES SERVICES SYSTEMD (sortir de root)
```ini
# /etc/systemd/system/flashback-api.service
[Service]
User=flashback-api
Group=flashback-api
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/flashback/uploads
CapabilityBoundingSet=
AmbientCapabilities=
```

### #9 — HASHER LES TOKENS DE RESET DE MOT DE PASSE
```python
import secrets
import hashlib

def create_reset_token(user_id: int, db: Session) -> str:
    raw_token = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw_token.encode()).hexdigest()
    db.add(ResetToken(
        user_id=user_id,
        token_hash=hashed,  # Stocker uniquement le hash
        expires_at=datetime.utcnow() + timedelta(hours=1)
    ))
    return raw_token  # Envoyer uniquement par email, jamais stocker en clair

def verify_reset_token(raw_token: str, db: Session) -> Optional[ResetToken]:
    hashed = hashlib.sha256(raw_token.encode()).hexdigest()
    return db.query(ResetToken).filter(
        ResetToken.token_hash == hashed,
        ResetToken.expires_at > datetime.utcnow(),
        ResetToken.used == False
    ).first()
```

### #10 — VÉRIFIER LES CRÉDITS AVANT DE CONSOMMER L'UPLOAD
```python
@router.post("/api/analyze")
async def analyze(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # VÉRIFIER EN PREMIER — avant tout traitement
    credits = get_user_credits(current_user.id, db)
    if credits < ANALYZE_COST:
        raise HTTPException(status_code=402, detail="Insufficient credits")
    
    # SEULEMENT ENSUITE traiter l'upload
    validated_file = await validate_and_save_upload(file)
    # ...
```

---

## PLAN DE CORRECTION PAR SÉVÉRITÉ

### P0 — CRITIQUE (À corriger avant tout lancement) — Effort : 5-8 jours

| # | Bug | Effort | Responsable |
|---|-----|--------|-------------|
| 1 | Rotation tous secrets compromis | 2h | DevOps |
| 2 | Fermeture ports 8000/8001/5432/superflus