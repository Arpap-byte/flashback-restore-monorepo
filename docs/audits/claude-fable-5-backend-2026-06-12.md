# Audit Backend Flashback Restore — Claude Fable 5

## Résumé exécutif

Le backend Flashback Restore est globalement bien structuré pour un SaaS de cette taille, avec de bons réflexes de production (idempotence Stripe, audit logs, remboursement de crédits en cas d'échec de job, validation magic bytes des uploads). Cependant, l'audit révèle **plusieurs failles critiques** : le bug connu #1 sur `subscription.deleted` est en réalité un problème de **lien manquant entre table `abonnements` et `utilisateurs`** (le webhook fonctionne mais la rétrogradation peut échouer silencieusement, et `invoice.paid` n'est pas idempotent au niveau financier), des **mismatches de schéma** (`Utilisateur.stripe_customer_id` est lu dans le code mais n'existe pas dans le modèle ORM → crash potentiel), une **vérification de crédits non atomique** entre `peut_restaurer` et `consommer_operation` (double consommation possible), et `credits_perpetuels` crédités mais **jamais consommés**. Le webhook Stripe ne vérifie pas non plus l'idempotence de manière atomique avec le traitement (marquage après traitement, sans transaction commune).

**Note globale : 5,5/10** — fondations correctes, mais des bugs financiers et d'intégrité référentielle qui doivent être corrigés avant toute montée en charge.

---

## 1. Architecture

### Points positifs
- Séparation claire : `api/` (routes), `services/` (logique métier), `db/` (queries + session), `models/` (ORM + Pydantic).
- Jobs longs délégués à ARQ — bon découplage HTTP/traitement.
- Scheduler APScheduler intégré au cycle de vie FastAPI avec `coalesce` et `max_instances=1`.
- Monitoring autonome (collectors/renderer/mailer/alerting) bien modulaire.

### Problèmes

**A1 — Logique métier dans les routes (couplage fort).** `routes.py` fait **1400+ lignes** et contient toute la logique webhook Stripe (lignes ~700-950), les requêtes SQL admin brutes, et la gestion des packs. Le webhook Stripe devrait vivre dans `services/stripe_webhook_handler.py`.

**A2 — Imports locaux disséminés.** Plus de 30 `from app.db.session import async_session` à l'intérieur de fonctions (routes.py, main.py, webhooks). C'est un symptôme de dépendances circulaires non résolues. La dépendance FastAPI `get_session()` existe dans `session.py` mais n'est **jamais utilisée**.

**A3 — `db/session.py` : docstring mensongère et configuration de pool fragile.**
```python
"""Utilise aiosqlite comme driver pour SQLite (WAL mode)."""  # FAUX : c'est PostgreSQL
_engine = create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20)
```
Si `DATABASE_URL` pointe vers SQLite (comme la docstring le suggère), `pool_size` provoquerait un crash. Pas de `pool_pre_ping=True` → connexions mortes après un restart PostgreSQL.

**A4 — Deux rate limiters redondants.** `limiter.py` (décorateur) et `rate_limit_middleware.py` (middleware) implémentent la même logique Redis. Les routes auth sont limitées **deux fois** (décorateur `@limiter.limit("5/minute")` + entrée `LIMITS["/api/auth/login"]`). Duplication à 95%.

**A5 — Événements de cycle de vie dépréciés.** `@app.on_event("startup")` / `shutdown` (main.py:~340) sont dépréciés depuis FastAPI 0.93 — migrer vers `lifespan`.

**A6 — `_arq_pool_lock = None` jamais utilisé** (routes.py:~95). Le singleton `_get_arq_pool()` a une race condition au démarrage (deux requêtes simultanées créent deux pools). Inoffensif mais code mort + bug latent.

**A7 — Monitoring : code suspect dans `collect_critical_only()`** (collectors.py, fin de fichier) :
```python
"ssl": _s if not isinstance(_s := None, Exception) else {},
"arq": _a if not isinstance(_a := None, Exception) else {},
```
Le walrus operator assigne `None` — `ssl` et `arq` sont **toujours `{}`/`None`**, donc les alertes SSL et ARQ **ne fonctionnent pas** dans le check 15 min. De plus, `arq` est collecté dans le `gather` mais le résultat affecté à `_` est jeté. **Bug réel : l'alerte "ARQ worker down" ne se déclenchera jamais via le check 15 min.**

**A8 — Worker ARQ : annotations de types incorrectes.** `restauration_job(utilisateur_id: int, travail_id: int)` alors que ce sont des UUID `str`. Pas d'impact runtime mais trompe le lecteur.

---

## 2. Sécurité

### Points positifs
- Vérification signature Svix (Clerk) et Stripe sur les webhooks.
- `/uploads` protégé par ownership avec anti-directory-traversal.
- Hash SHA-256 des tokens de reset password.
- Headers de sécurité (CSP, HSTS, X-Frame-Options).
- Anti-énumération email (202 sur register, message générique sur forgot-password).

### Problèmes

**S1 — 🔴 X-Forwarded-For spoofable pour le rate limiting.** Dans `rate_limit_middleware.py:get_client_ip()` et `limiter.py`, le header `X-Forwarded-For` est pris tel quel. Si Traefik ne strip pas les XFF entrants (configuration à vérifier), un attaquant peut **bypasser tout le rate limiting** en envoyant `X-Forwarded-For: <ip-aléatoire>`. Le brute-force sur `/api/auth/login` devient illimité.

**S2 — 🔴 Comparaison admin key non constant-time.** Partout : `admin_key != ADMIN_API_KEY`. Utiliser `hmac.compare_digest()`. Cette vérification est dupliquée **9 fois** dans routes.py — devrait être une dépendance FastAPI unique.

**S3 — 🔴 Token download dans les query strings.** `creer_token_telechargement` génère des JWT passés en `?token=...`. Ces URL finissent dans : logs Traefik, historique navigateur, header Referer. Le token donne accès à **tous les fichiers de l'utilisateur** pendant 30 min, pas uniquement au fichier ciblé. Mitigation : scope au fichier (`payload["file"] = filename`) et `Referrer-Policy` est déjà en place (bien), mais les logs proxy restent un vecteur.

**S4 — 🟠 Token download avec scope non vérifié.** `creer_token_telechargement` ajoute `"scope": "download"` mais `decoder_token` ne vérifie **jamais** ce scope. Inversement, un token download (30 min) est accepté comme token d'authentification complet sur n'importe quel endpoint — il passe par `_trouver_ou_creer_utilisateur` via le `sub`. **Un token download fuité = session complète de 30 min.**

**S5 — 🟠 Consentement checkout falsifiable.** `POST /api/consents/checkout` accepte un email arbitraire sans authentification ni vérification. N'importe qui peut enregistrer des consentements pour `victime@example.com`. Pour une preuve légale RGPD, c'est problématique (valeur probante affaiblie). De plus, `creer_session_paiement` hardcode `"cgu_acceptees": "true"` dans les metadata Stripe sans aucune vérification réelle quand `ENFORCE_CONSENT=false`.

**S6 — 🟠 `asyncio.create_task` dans contexte sync.** `webhooks.py:_verifier_signature()` (fonction **sync**) appelle `asyncio.create_task(log_security_event(...))` — cela lèvera `RuntimeError: no running event loop` ou créera une task orpheline jamais awaited selon le contexte. L'audit de sécurité des signatures invalides **n'est probablement jamais enregistré**.

**S7 — 🟡 Validation upload incomplète sur `/restore` avec `image_importee_id`.** Quand l'image vient de la galerie, aucune re-validation magic bytes n'est faite (le fichier a été validé à l'import, acceptable, mais la lecture `chemin_source.read_bytes()` sans limite de taille re-charge potentiellement 20 Mo en mémoire).

**S8 — 🟡 CSP `img-src https:`** autorise toutes les origines HTTPS pour les images — large mais courant.

**S9 — 🟡 `_extraire_email` fallback placeholder** (webhooks.py) : retourne le premier email même si c'est un placeholder, contredisant le refus strict dans `auth.py`. Incohérence : le webhook peut créer un compte avec email placeholder que le login refuserait.

**S10 — 🟢 Logs d'emails en clair.** `auth.py` loggue `f"Nouvel utilisateur créé : {body.email}"` alors que `audit.py` masque soigneusement les emails. Incohérent au regard du RGPD.

---

## 3. Modèle de données (PostgreSQL)

### Problèmes

**D1 — 🔴 Colonnes lues mais inexistantes dans le modèle.** `user.py:/subscription` et `routes.py:/stripe/portal` lisent `user_row.get("stripe_customer_id")` et `stripe_subscription_id` sur le dict issu de `Utilisateur`. **Ces colonnes n'existent pas** dans `db_models.py:Utilisateur` ni dans aucune migration. `lister_utilisateurs_abonnes()` (queries.py) fait `Utilisateur.stripe_customer_id.isnot(None)` → **`AttributeError` au runtime**. Conséquences :
- `GET /api/user/subscription` retourne toujours `stripe: None` (`.get()` masque le bug) ;
- `POST /api/stripe/portal` retourne toujours 400 "Aucun abonnement Stripe trouvé" → **les 3 abonnés premium ne peuvent pas accéder au portail client** ;
- Le job `run_subscription_reminders` (P3.4) **crash à chaque exécution** (10h UTC quotidien) — vérifier les logs.

**D2 — 🔴 Pas de FK entre `abonnements` et `utilisateurs`.** Le lien se fait par `email_utilisateur` (String, non indexé, non FK). Si l'utilisateur change d'email (sync Clerk `user.updated`), **le lien abonnement↔utilisateur est cassé** : `subscription.deleted` ne retrouvera plus l'utilisateur → **plan premium jamais rétrogradé**. C'est très probablement la cause racine du bug connu #1.

**D3 — 🟠 Types incohérents.** `Abonnement.derniere_attribution_credits` est `String` (ISO) au lieu de `DateTime`. `est_abonne`/`utilise`/`reussite` sont `Integer` au lieu de `Boolean`. `Travail.job_externe_id` non indexé alors que `obtenir_travail_par_job_externe` fait un scan dessus.

**D4 — 🟠 CheckConstraints divergentes migration vs ORM.** Migration initiale : `type IN ('analyse','restauration','animation')` ; ORM : ajoute `'colorisation'`. Aucune migration ne modifie `ck_travaux_type` ni `ck_consommation_type` ni `ck_essais_type`. **Si la contrainte DB est celle de la migration initiale, tout INSERT de colorisation viole la contrainte.** (Probablement masqué car `init_db()` avec `create_all` ne touche pas aux tables existantes — mais l'écart migration/ORM est une bombe à retardement.) À vérifier en prod : `\d travaux`.

**D5 — 🟠 `init_db()` (create_all) + Alembic en parallèle.** Le startup appelle `Base.metadata.create_all`, court-circuitant Alembic. Dangereux : sur une DB neuve, `alembic_version` est vide et les futures migrations échoueront ou s'appliqueront sur un schéma déjà créé.

**D6 — 🟡 Pas de `ondelete` sur les FK** (sauf la table supprimée `imported_photos`). `supprimer_compte` anonymise (bien), mais une suppression brute d'utilisateur échouerait sur les FK.

**D7 — 🟡 SQL brut massif dans routes.py.** Toutes les requêtes admin utilisent `sa_text()` avec bind params — **pas d'injection SQL détectée** (paramètres correctement bindés partout, y compris la construction dynamique dans `admin_liste_travaux` qui concatène uniquement des fragments statiques). Mais c'est fragile et non typé.

**D8 — 🟡 `_plan_cache` in-memory** (queries.py) : cache 60s du plan par user. Avec plusieurs workers uvicorn, incohérence possible (un user upgrade et reste "gratuit" 60s sur un autre worker). Acceptable à cette échelle, à documenter.

**D9 — 🟡 Migration `5b14e3c33acb`** : `down_revision` pointe vers `8dc346ab91ac` mais le docstring dit `Revises: 31fffebd0c35` — révision `31fffebd0c35` référencée dans deux fichiers mais absente du repo. Historique de migrations à auditer (`alembic history`).

---

## 4. Qualité du code

**Q1 — Duplication massive.** 
- Vérification admin key : 9 occurrences identiques → dépendance `verifier_admin`.
- Upload B2 avec retry : dupliqué dans `restauration_job` et `animation_job` (worker.py) → extraire `_upload_b2_avec_retry()`.
- Bloc "upload B2 fallback local" : dupliqué dans `/restore` et `/colorize`.
- SMTP : 3 implémentations (mail.py, contact_routes.py, scheduler.py, mailer.py) — 4 en fait.
- `_extraire_ip` (consent_routes.py) ≈ `get_client_ip` (rate_limit_middleware.py) ≈ `extraire_ip_et_ua` (audit.py).

**Q2 — Imports morts dans routes.py.** `ImageEnhance`, `ImageFilter`, `creer_utilisateur_oauth`, `obtenir_utilisateur_par_oauth` (auth.py), `consentement_actif`, `Header`, etc. Le module `schemas.py` contient `AnimationRequete` (texte/voix) jamais utilisé — vestige de l'ancienne API D-ID.

**Q3 — Gestion d'erreurs : exceptions avalées dans le webhook Stripe.** Chaque branche `except Exception: logger.exception(...)` puis **continue et marque l'event comme traité**. Si la créditation échoue (DB down ponctuel), Stripe reçoit 200, l'event est marqué traité → **crédits définitivement perdus, pas de retry Stripe**. Il faut retourner 500 pour que Stripe rejoue.

**Q4 — Fuite de détails d'erreur.** `routes.py:/analyze` : `detail=f"Erreur lors de l'analyse : {str(e)}"` — peut exposer des messages internes Gemini (incluant potentiellement des fragments d'URL avec clé si une httpx error remonte). Idem `/colorize` et `/api/job/{job_id}`.

**Q5 — `coloriser_standalone` : `analyse=None  # type: ignore`** sur un champ Pydantic requis (`analyse: AnalyseReponse`) — lèvera une `ValidationError` à la construction du `RestaurationReponse`... sauf si Pydantic v1/laxisme. **À tester : l'endpoint `/colorize` plante probablement en réponse.** En Pydantic v2, `AnalyseReponse` sans default → erreur de validation → 500 après consommation du crédit (remboursé ? non — pas de remboursement dans `/colorize` en cas d'erreur de sérialisation post-succès).

**Q6 — `test_auth.py` utilise `TestClient(app)` au niveau module** → exécute le startup (init_db, scheduler) sur la vraie config. Les tests touchent potentiellement la prod si `.env` est chargé. `conftest.py` patche `queries.async_session` mais pas `app.db.session.async_session` utilisé directement par routes.py → fuites possibles vers la vraie DB pendant les tests.

**Q7 — Typage et docstrings** : globalement bons (docstrings français systématiques). Quelques annotations fausses (worker.py D8/A8).

---

## 5. Performance

**P1 — 🔴 N+1 et tokens redondants dans `/api/user/history`.** Pour chaque travail, `_vers_url` appelle `creer_token_telechargement` (3× par travail × 50 travaux = **150 signatures JWT par requête**), alors qu'un `token_dl` est déjà généré en haut de la fonction et... jamais utilisé. Même problème dans `/api/library` (1 token par image).

**P2 — 🔴 Course de crédits (TOCTOU).** Dans `/restore` et `/animate` : `peut_restaurer()` (lecture) puis bien plus tard `consommer_operation()` (écriture). Entre les deux : écriture disque, upload B2, enqueue ARQ. Deux requêtes simultanées avec 1 crédit passent toutes les deux le check. `consommer_credits` a un `FOR UPDATE` correct et refusera la 2ᵉ — **mais le job ARQ est déjà enqueué** : l'exception `RuntimeError` de `consommer_operation` fait échouer la requête HTTP en 500 **alors que le job tourne quand même** → traitement gratuit. Ordre correct : consommer (atomique) → enqueue → rembourser si enqueue échoue.

**P3 — 🟠 Uploads bloquent l'event loop.** `chemin.write_bytes(contenu)` (jusqu'à 20 Mo), `uploader_bytes` (boto3 **synchrone**) et `magic.from_buffer` sont appelés directement dans les handlers async → blocage de l'event loop. Utiliser `asyncio.to_thread`. Le worker fait pareil avec `chemin_final.read_bytes()`.

**P4 — 🟠 Sessions DB multiples par requête.** `/api/user/me` ouvre ~6 sessions (obtenir_utilisateur, essais, plan, retention, + 2 counts). Chaque appel queries.py ouvre sa propre session/transaction. À 10-20 users c'est OK ; pattern à corriger avant de scaler (passer la session en dépendance).

**P5 — 🟡 `supprimer_tous_travaux_utilisateur`** charge tous les objets ORM puis `delete` un par un — utiliser `DELETE WHERE`.

**P6 — 🟡 Pas de `pool_pre_ping`** ni de timeout sur l'engine (cf. A3).

**P7 — 🟡 `psutil.cpu_percent(interval=0.1)`** dans `collect_system` (async) : bloque l'event loop 100 ms — mineur.

---

## 6. Endpoints API

**E1 — Codes HTTP incohérents.** `/restore` retourne **402** si crédits insuffisants, `/animate` retourne **403** pour le même cas. `/library/upload` retourne 413 pour fichier trop gros, `_valider_upload` retourne 400. Standardiser (402 pour crédits, 413 pour taille).

**E2 — Réponses non typées.** `/restore` et `/animate` retournent des dicts bruts (pas de `response_model`), alors que `/colorize` a `response_model=RestaurationReponse`. `/animate/{job_id}` (déprécié) ne met pas de token sur `url_video` alors que `/animate/travail/{id}` oui — incohérence qui casse l'affichage selon l'endpoint utilisé.

**E3 — Paramètres admin non validés.** `consulter_audit_logs(limite: int = 50)` : `limite` est clampé à 200 mais `offset` ne l'est pas ; `admin_liste_utilisateurs(limite: int = 50)` sans borne (un `limite=10000000` est passé tel quel à SQL).

**E4 — `CheckoutRequete.plan` pattern obsolète.** `pattern="^(decouverte|premium|annuel|30|50|110)$"` mélange abonnements et anciens packs crédits (30/50/110) alors que les nouveaux packs sont S/M/L/XL via un autre endpoint. Le même schéma sert deux endpoints différents — confusion garantie.

**E5 — `/api/user/history` : `request: Request = None  # type: ignore`** — paramètre mort.

**E6 — Documentation** : docs désactivées en prod (bien), docstrings riches (bien). Mais la doc de `/animate/{job_id}` dit "Interroge la base de données locale" tout en s'appelant "statut via job ARQ" — confus.

**E7 — `lister_packs_credits` avec `obtenir_utilisateur_courant`** : `utilisateur.get("est_abonne")` — mais `obtenir_utilisateur_courant` retourne seulement `{"id", "email"}` → `est_abonne` est **toujours absent** → **les abonnés ne voient jamais le prix remisé -20%**. Même bug dans `creer_checkout_pack` : `utilisateur.get("est_abonne")` sur le dict `{id, email}` → toujours False → **les abonnés paient plein tarif les packs**. 🔴 Bug métier réel.

---

## 7. Paiements (Stripe)

**ST1 — 🔴 Bug connu #1 confirmé et expliqué.** Le handler `customer.subscription.deleted` existe et semble correct, MAIS :
1. Il dépend de `abonnements.email_utilisateur` — si l'email a changé (D2), l'utilisateur n'est pas retrouvé, et le `logger.info("Utilisateur rétrogradé")` n'est jamais émis **sans aucun warning** (le `if utilisateur:` échoue silencieusement).
2. La séquence n'est pas atomique : `mettre_a_jour_abonnement` (commit) → `obtenir_abonnement` → `mettre_a_jour_plan_utilisateur` (commit) → update `est_abonne` (commit). Un crash entre les étapes laisse un état incohérent.
3. **`mettre_a_jour_plan_utilisateur` force `est_abonne=1`** même pour plan="gratuit", corrigé après coup par un UPDATE séparé — design fragile. Pour les 3 abonnements expirant le 15 juin 2026 : **vérifier manuellement que `abonnements.email_utilisateur` correspond bien à l'email actuel des 3 utilisateurs**, sinon ils resteront premium.

**ST2 — 🔴 Idempotence non atomique.** Le flux est : check `stripe_event_deja_traite` → traiter → `marquer_stripe_event_traite`. Deux livraisons simultanées du même event (Stripe retry) passent toutes deux le check → **double créditation possible**. De plus, le marquage final lèvera `IntegrityError` (contrainte unique) → 500 → Stripe re-livre → boucle. Solution : `INSERT ... ON CONFLICT DO NOTHING RETURNING` **en début** de traitement, dans la même transaction que les crédits.

**ST3 — 🔴 `invoice.paid` : pas d'idempotence financière interne.** Les opérations `crediter_utilisateur` + `mettre_a_jour_attribution_credits` sont des commits séparés. Si le process crash entre les deux, un redelivery est bloqué par l'idempotence event_id... sauf que le marquage final n'a pas eu lieu → re-créditation. Et `derniere_attribution_credits` n'est jamais utilisé comme garde-fou (lu, loggé, jamais comparé).

**ST4 — 🟠 Échecs de traitement → event quand même marqué traité** (cf. Q3). Si `obtenir_utilisateur_par_email` retourne None (compte pas encore créé via Clerk — race condition réelle : paiement avant premier login backend), le webhook loggue un warning, marque l'event traité, et **les crédits sont perdus à jamais**. Il faut soit retourner 500 (retry Stripe pendant 3 jours), soit créer le compte à la volée depuis l'email.

**ST5 — 🟠 `creer_abonnement` ne capture pas `cancel_at_period_end`** ni la fin de période. La table locale ne sait pas que les 3 abonnements premium sont en `cancel_at_period_end` — le job de relance J-3 enverra un email "renouvelez" à des gens qui ont résilié (s'il ne crashait pas déjà, cf. D1).

**ST6 — 🟠 Packs S/M/L/XL : prix dynamique via `price_data`** au lieu de Price IDs Stripe — fonctionnel mais le prix est contrôlé côté serveur (OK) ; en revanche `est_abonne` cassé (E7) rend la remise inopérante.

**ST7 — 🟡 `checkout.session.completed` abonnement : `obtenir_utilisateur_par_email` appelé hors de la session transactionnelle** passée à `creer_abonnement`/`crediter_utilisateur` — lecture hors transaction, OK fonctionnellement mais incohérent.

**ST8 — 🟡 Webhook consent enforcement** : `ENFORCE_CONSENT=false` par défaut → en prod, les checkouts passent **sans aucun consentement vérifié**, alors que le contexte métier dit "consentements obligatoires". Vérifier la valeur en prod.

**ST9 — 🟡 `credits_perpetuels` crédités (webhook pack) mais jamais consommés.** `consommer_credits` ne touche que `essais_restants` + `credits`. `peut_restaurer` les compte dans le total mais `consommer_credits` échouera si seuls des perpétuels sont disponibles → **un utilisateur qui achète un pack avec 0 crédit classique paie et ne peut rien faire** (peut_restaurer dit oui, consommer dit non → 500 sur `/restore` après enqueue). 🔴 En fait critique : bug financier direct.

---

## 8. Plan d'action priorisé

| Priorité | Problème | Fichier(s) | Impact | Effort |
|---|---|---|---|---|
| 🔴P0 | `credits_perpetuels` crédités mais jamais consommables (ST9) | `db/queries.py:consommer_credits`, `services/credits.py` | Client paie, service refuse → litige/remboursement | 2-4h |
| 🔴P0 | `stripe_customer_id`/`stripe_subscription_id` absents du modèle `Utilisateur` → portail Stripe cassé, job relances crash | `models/db_models.py`, migration Alembic, `queries.py:lister_utilisateurs_abonnes` | 3 abonnés sans portail ; crash quotidien scheduler | 2h |
| 🔴P0 | Idempotence webhook non atomique + events marqués traités malgré échec (ST2/ST4/Q3) | `api/routes.py:webhook_stripe`, `db/queries.py` | Double créditation ou crédits perdus | 4-6h |
| 🔴P0 | TOCTOU crédits : enqueue avant consommation (P2) | `api/routes.py:/restore,/animate` | Traitements gratuits sous concurrence | 2h |
| 🔴P0 | Vérifier lien email abonnements↔utilisateurs pour les 3 premium expirant 15/06 (ST1/D2) | DB prod + `db_models.py` (FK `utilisateur_id` sur `abonnements`) | Bug connu #1 : premium éternel | 1h vérif + 4h fix |
| 🔴P0 | Rate limiting spoofable via XFF (S1) | `rate_limit_middleware.py`, `limiter.py`, config Traefik | Brute-force login illimité | 1-2h |
| 🟠P1 | Token download = session complète, scope non vérifié (S4) | `auth.py:decoder_token`, `main.py:/uploads` | Élévation de privilège sur token fuité | 2h |
| 🟠P1 | Remise abonné packs jamais appliquée (`est_abonne` absent du dict auth) (E7) | `api/routes.py:lister_packs_credits, creer_checkout_pack`, `auth.py` | Abonnés surfacturés -20% | 1h |
| 🟠P1 | `/colorize` : `analyse=None` sur champ Pydantic requis (Q5) | `api/routes.py`, `models/schemas.py` | Endpoint probablement cassé (500 après débit) | 30min |
| 🟠P1 | CheckConstraints DB divergentes ORM/migrations (D4) | migration Alembic | INSERT colorisation peut échouer | 1h |
| 🟠P1 | `asyncio.create_task` dans fonction sync (S6) | `api/webhooks.py:_verifier_signature` | Audit sécurité non enregistré / RuntimeError | 30min |
| 🟠P1 | Alertes SSL/ARQ mortes dans check 15 min (A7) | `services/monitoring/collectors.py:collect_critical_only` | Worker ARQ down non détecté | 30min |
| 🟠P1 | Exceptions webhook → 200 silencieux (Q3) | `api/routes.py:webhook_stripe` | Pas de retry Stripe sur échec DB | inclus P0 webhook |
| 🟡P2 | Comparaison admin key non constant-time + duplication ×9 (S2/Q1) | `api/routes.py` | Timing attack théorique ; maintenabilité | 1h |
| 🟡P2 | Supprimer `init_db()` create_all, migrer 100% Alembic (D5) | `main.py`, `db/session.py` | Dérive de schéma | 2h |
| 🟡P2 | Fusionner les 2 rate limiters (A4) | `limiter.py`, `rate_limit_middleware.py` | Double comptage, maintenance | 2h |
| 🟡P2 | I/O bloquantes dans handlers async (P3) | `api/routes.py`, `storage.py`, `worker.py` | Latence sous charge | 3h |
| 🟡P2 | Capture `cancel_at_period_end` en local (ST5) | `services/stripe_service.py`, modèle Abonnement | Relances inappropriées | 2h |
| 🟢P3 | Extraire webhook Stripe dans un service (A1) | `api/routes.py` → `services/` | Maintenabilité | 4h |
| 🟢P3 | Lifespan FastAPI, dépendance get_session, dead code (A5/A2/Q2) | `main.py`, divers | Dette technique | 4h |
| 🟢P3 | N+1 tokens dans /history (P1) | `api/user.py` | CPU gaspillé | 30min |

---

## 9. Quick Wins (< 30 min chacun)

### QW1 — Fix N+1 tokens dans `/api/user/history` (api/user.py)
```diff
-def _vers_url(chemin: str | None, utilisateur_id: str) -> str | None:
+def _vers_url(chemin: str | None, token_dl: str) -> str | None:
     if not chemin:
         return None
-    from app.auth import creer_token_telechargement
-
     nom_fichier = os.path.basename(chemin)
-    url = f"/uploads/{nom_fichier}"
-    token_dl = creer_token_telechargement(utilisateur_id)
-    url += f"?token={token_dl}"
-    return url
+    return f"/uploads/{nom_fichier}?token={token_dl}"
```
```diff
         resultat.append({
             ...
-            "url_original": _vers_url(t.get("chemin_photo"), utilisateur["id"]),
-            "url_resultat": _vers_url(t.get("chemin_resultat"), utilisateur["id"]),
-            "url_animation": _vers_url(t.get("chemin_animation"), utilisateur["id"]),
+            "url_original": _vers_url(t.get("chemin_photo"), token_dl),
+            "url_resultat": _vers_url(t.get("chemin_resultat"), token_dl),
+            "url_animation": _vers_url(t.get("chemin_animation"), token_dl),
```

### QW2 — Comparaison constant-time + dépendance admin (api/routes.py)
```diff
+import hmac
+
+async def verifier_admin(request: Request):
+    admin_key = request.headers.get("X-Admin-Key", "")
+    if not ADMIN_API_KEY or not hmac.compare_digest(admin_key, ADMIN_API_KEY):
+        raise HTTPException(status_code=403, detail="Accès non autorisé.")
```
Puis sur chaque route admin :
```diff
-@router.get("/stats", response_model=StatsReponse)
-async def statistiques(request: Request):
-    admin_key = request.headers.get("X-Admin-Key")
-    if not ADMIN_API_KEY or admin_key != ADMIN_API_KEY:
-        raise HTTPException(status_code=403, detail="Accès non autorisé. Token admin requis.")
+@router.get("/stats", response_model=StatsReponse, dependencies=[Depends(verifier_admin)])
+async def statistiques(request: Request):
```

### QW3 — Fix `asyncio.create_task` dans contexte sync (api/webhooks.py)
```diff
     except WebhookVerificationError as e:
         logger.warning("Signature webhook Clerk invalide: svix-id=%s, erreur=%s", svix_id, e)
-        # Audit de sécurité
-        from app.services.audit import log_security_event
-        import asyncio
-        asyncio.create_task(log_security_event(
-            "webhook_signature_invalide",
-            detail=f"svix-id={svix_id}, timestamp={svix_timestamp}",
-        ))
         raise HTTPException(status_code=401, detail="Invalid signature")
```
Et déplacer l'audit dans le handler async `clerk_webhook` :
```diff
     try:
         _verifier_signature(request, payload)
-    except HTTPException:
-        raise  # 401/400 déjà levé
+    except HTTPException as exc:
+        if exc.status_code == 401:
+            from app.services.audit import log_security_event
+            await log_security_event("webhook_signature_invalide",
+                                     detail=f"svix-id={request.headers.get('svix-id','')}")
+        raise
```

### QW4 — Fix alertes SSL/ARQ mortes (services/monitoring/collectors.py)
```diff
 async def collect_critical_only() -> dict:
     """Collecte légère pour les alertes toutes les 15 minutes."""
-    services, _, _, system, _ = await asyncio.gather(
+    services, ssl, system, arq = await asyncio.gather(
         collect_services(),
         collect_ssl(),
-        asyncio.sleep(0),  # skip DB pour les alertes rapides
         collect_system(),
         collect_arq_worker(),
         return_exceptions=True,
     )
 
     now = datetime.now(timezone.utc)
 
     return {
         "timestamp": now.isoformat(),
         "date_fr": now.strftime("%d/%m/%Y %H:%M"),
         "services": services if not isinstance(services, Exception) else {"error": str(services)},
-        "ssl": _s if not isinstance(_s := None, Exception) else {},
+        "ssl": ssl if not isinstance(ssl, Exception) else {},
         "system": system if not isinstance(system, Exception) else {},
-        "arq": _a if not isinstance(_a := None, Exception) else {},
+        "arq": arq if not isinstance(arq, Exception) else {},
     }
```

### QW5 — Fix `/colorize` réponse Pydantic invalide (models/schemas.py)
```diff
 class RestaurationReponse(BaseModel):
     """Réponse après restauration d'une photo."""
 
     message: str = Field(..., description="Message de succès")
-    analyse: AnalyseReponse
+    analyse: Optional[AnalyseReponse] = Field(
+        default=None, description="Analyse des défauts (absente pour la colorisation standalone)"
+    )
```

### QW6 — Fix XFF spoofing (rate_limit_middleware.py) — sous réserve que Traefik soit le seul point d'entrée
```diff
+# Liste des IP de confiance autorisées à fournir X-Forwarded-For (Traefik local)
+TRUSTED_PROXIES = {"127.0.0.1", "::1"}
+
 def get_client_ip(request: Request) -> str:
     """Extrait l'IP client, en tenant compte du proxy Traefik."""
-    forwarded = request.headers.get("X-Forwarded-For", "")
-    if forwarded:
-        return forwarded.split(",")[0].strip()
     client = request.client
-    return client.host if client else "unknown"
+    peer_ip = client.host if client else "unknown"
+    forwarded = request.headers.get("X-Forwarded-For", "")
+    if forwarded and peer_ip in TRUSTED_PROXIES:
+        # Prendre la DERNIÈRE IP ajoutée par notre proxy (la seule de confiance)
+        return forwarded.split(",")[-1].strip()
+    return peer_ip
```

### QW7 — Vérifier le scope du token download (main.py:/uploads + auth.py)
```diff
     if utilisateur is None and token:
         # Fallback : token JWT passé en query parameter (pour <img src>)
         try:
             payload = decoder_token(token)
+            # Un token query-param doit être un token de téléchargement OU un token complet,
+            # mais un token "download" ne doit JAMAIS être accepté ailleurs.
             utilisateur = await _trouver_ou_creer_utilisateur(payload)
         except Exception:
             pass
```
Et dans `auth.py:obtenir_utilisateur_courant`, refuser les tokens à scope download sur les routes API :
```diff
     try:
         payload = decoder_token(token)
+        if payload.get("scope") == "download":
+            raise HTTPException(status_code=401,
+                                detail="Token de téléchargement non valide pour cette opération.")
     except jwt.ExpiredSignatureError:
```

### QW8 — Logs : ne plus logger les emails en clair (api/auth.py)
```diff
-    logger.info(f"Nouvel utilisateur créé : {body.email}")
+    logger.info(f"Nouvel utilisateur créé : id={utilisateur_id}")
...
-    logger.info(f"Connexion réussie : {utilisateur['email']}")
+    logger.info(f"Connexion réussie : id={utilisateur['id']}")
```

### QW9 — Vérification urgente en prod (pas un diff, une commande)
Pour le bug #1 et les 3 abonnements du 15 juin :
```sql
-- Vérifier que le lien email abonnement ↔ utilisateur est intact
SELECT a.stripe_subscription_id, a.email_utilisateur, a.statut, u.id, u.email, u.plan, u.est_abonne
FROM abonnements a
LEFT JOIN utilisateurs u ON lower(u.email) = lower(a.email_utilisateur)
WHERE a.statut = 'actif';
-- Toute ligne avec u.id NULL = utilisateur qui ne sera JAMAIS rétrogradé.

-- Vérifier les contraintes réelles de travaux (D4)
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'travaux'::regclass;
```

---

*Fin du rapport. Les corrections P0 représentent environ 2-3 jours de travail et doivent être traitées avant le 15 juin 2026 (expiration des abonnements premium) et avant toute campagne d'acquisition.*