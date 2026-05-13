# RAPPORT D'AUDIT — SUITE DE TESTS SAAS RESTAURATION PHOTO

---

## 1. COUVERTURE FONCTIONNELLE — 4/10

### Ce qui est couvert
- Auth : rejection des tokens absents/invalides ✓
- Crédits : CRUD basique (créer, créditer, consommer, lire) ✓
- Crédits : logique essais gratuits vs crédits payants ✓
- Stripe : idempotence au niveau DB ✓
- Stripe : validation de signature webhook ✓

### Ce qui manque — et c'est catastrophique

**Flux métier core = 0 tests**
- Le pipeline complet upload → analyse → restauration → livraison n'existe pas
- `POST /api/analyze` : testé uniquement pour le 401, jamais pour son fonctionnement
- `POST /api/restore` : idem — zéro test du flux happy path
- La file ARQ/Redis : aucun test. Zéro. Le cœur du produit est une boîte noire

**Stockage B2 = 0 tests**
- Upload vers B2 : non testé
- Download/génération d'URLs signées : non testé
- Gestion des erreurs B2 (timeout, quota, erreur réseau) : non testée

**Stripe Checkout = partiellement testé**
- `checkout.session.completed` : le webhook le plus critique (celui qui crédite l'utilisateur) n'est pas testé end-to-end avec un vrai payload Stripe
- La logique de crédit après paiement n'est pas vérifiée
- Aucun test pour `payment_intent.payment_failed`, `customer.subscription.deleted`

**Auth Clerk = tests superficiels**
- Token expiré : non testé (différent de "token invalide")
- Token d'un autre tenant/application : non testé
- JWKS fetch failure (réseau mort) : non testé
- Un seul endpoint positif testé (health). Zéro test "token valide → accès accordé"

**Utilisateur = non testé**
- Création automatique du profil lors du premier login Clerk
- `GET /api/user/me` avec un vrai utilisateur : non testé
- Mise à jour du profil : non testée

**Admin = sous-testé**
- `/api/stats` avec X-Admin-Key valide : non testé (seulement le 403)

---

## 2. QUALITÉ DES TESTS — 5/10

### Problèmes structurels

**`test_upload_sans_auth` est un mensonge documenté**
```python
def test_upload_sans_auth():
    """POST /api/upload sans token doit retourner 404 (l'endpoint n'existe pas encore)"""
    res = client.post("/api/analyze")
    assert res.status_code in (401, 422), ...  # Accept 422 !
```
Un test qui accepte 422 pour "vérifier l'auth" ne teste rien d'utile. Si FastAPI valide le body avant la dépendance d'auth, le test passe en 422 et l'endpoint n'est **pas protégé** selon la définition du test. C'est un faux positif potentiel camouflé en succès. Même logique pour `test_upload_token_invalide`.

**Le test d'atomicité est une tautologie**
```python
lock = asyncio.Lock()
async def consommer_un():
    async with lock:  # Sérialisation manuelle
        return await consommer_credit(...)
```
On teste que du code séquentiel s'exécute séquentiellement. Ce test ne prouve **absolument rien** sur l'atomicité de `SELECT FOR UPDATE` en PostgreSQL. C'est du théâtre. Le seul scénario dangereux — deux transactions PostgreSQL simultanées — n'est pas testé.

**Assertions trop couplées aux messages d'erreur**
```python
assert res.json()["detail"] == "Authentification requise."
assert res.json()["detail"] == "Token invalide."
assert "Plus de crédits" in res["raison"]
assert "Crédits insuffisants" in raison
```
Quatre strings hardcodées dans les tests. Changer un message d'erreur casse plusieurs tests sans raison fonctionnelle. Les assertions devraient porter sur le code HTTP et la structure, pas le libellé exact.

**`asyncio.run(init_db())` au module level dans test_stripe.py**
```python
asyncio.run(init_db())  # Ligne 36
```
Exécuté à l'import du module, avant la configuration pytest. Provoque des comportements non déterministes si l'event loop est déjà actif (pytest-asyncio). Crée une DB partagée entre tous les tests de la classe sans isolation.

**Fixtures de scope `function` qui recréent le moteur à chaque test**
```python
@pytest_asyncio.fixture(scope="function")
async def db_session():
    global _engine, _test_factory  # Variables globales mutables
    _engine = create_async_engine(TEST_DB_URL, echo=False)
```
Utilisation de `global` dans une fixture = dette technique immédiate. Si deux tests tournent en parallèle (`-n auto`), `_engine` et `_test_factory` sont écrasés mutuellement.

**Noms de tests approximatifs**
- `test_consommer_credit_atomique` → ne teste pas l'atomicité
- `test_atomicite_haute_concurrence` → pas de concurrence réelle
- `test_upload_sans_auth` → teste `/api/analyze`, pas `/api/upload`

---

## 3. FIABILITÉ — 4/10

### Race conditions et non-déterminisme

**SQLite shared memory et URI instable**
```python
TEST_DB_URL = "sqlite+aiosqlite:///file:test_credits_mem?mode=memory&cache=shared"
```
Le `cache=shared` avec plusieurs connexions sur une base in-memory en URI mode est documenté comme instable selon les versions de SQLite. Si deux fixtures créent simultanément leur engine avec le même nom, les `create_all` / `drop_all` interfèrent.

**`asyncio.run(init_db())` crée une DB fichier SQLite en mode test**
Dans `test_stripe.py`, `init_db()` initialise vraisemblablement la DB de l'application (pas la DB de test). Les tests Stripe opèrent donc sur une DB persistante, partagée entre runs. Si un test précédent a laissé des `stripe_events`, les assertions d'idempotence peuvent diverger.

**Timestamps dans `_generer_signature_stripe`**
```python
timestamp = str(int(time.time()))
```
Stripe valide que le timestamp n'est pas trop ancien (tolérance de 300 secondes par défaut). En CI avec une horloge décalée ou un test qui tourne lentement, ce test peut échouer de façon non reproductible. Aucun mock du timestamp.

**`test_stripe_event_double_marquage` pollue la DB**
```python
await marquer_stripe_event_traite(eid, "checkout.session.completed")
# IntegrityError levée, mais le premier insert est committé
```
Après ce test, la DB contient un event. Si `init_db()` ne nettoie pas entre les tests, les tests suivants voient des données parasites. Pas de teardown dans `TestStripeEventIdempotence`.

**Dépendance implicite à `STRIPE_WEBHOOK_SECRET`**
```python
from app.config import STRIPE_WEBHOOK_SECRET
```
Si cette variable d'environnement n'est pas définie en CI, l'import échoue silencieusement ou utilise une valeur par défaut qui ne correspond pas à celle utilisée par le webhook handler. Le test `test_webhook_stripe_evenement_valide` passe alors en 400 sans explication claire.

**Les tests de classe `TestStripeEventIdempotence` sont stateful sans isolation**
Aucune fixture de setup/teardown. Les tests dépendent de l'état de la DB initialisée par `asyncio.run(init_db())`. Réordonner les tests (ce que pytest peut faire) pourrait les casser.

---

## 4. MAINTENABILITÉ — 5/10

### Points positifs
- Docstrings présentes sur chaque test
- Structure en classes thématiques cohérente
- Commentaires sur les limitations SQLite vs PostgreSQL

### Problèmes

**Duplication massive de la logique "épuiser les essais"**
```python
# Apparaît 6 fois dans test_credits.py :
for _ in range(3):
    await consommer_credit(uid, "restauration", "travail_x")
```
Le nombre d'essais gratuits (3) est hardcodé. Si le business change à 5 essais, c'est 6 endroits à corriger, dont certains commentaires contradictoires.

**Pas de `conftest.py`**
Chaque fichier de test réinvente sa propre infrastructure (engine, session, client). Un `conftest.py` avec les fixtures partagées éviterait 80% de la duplication.

**`sys.path.insert` redondant**
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```
Présent dans `test_credits.py` et `test_stripe.py`. Signe que `pyproject.toml` / `setup.cfg` ne configure pas correctement le package. À corriger à la racine.

**Commentaires qui excusent les lacunes plutôt qu'ils ne les documentent**
```python
# Note: SQLite ne supporte pas FOR UPDATE au sens PostgreSQL.
# On utilise un asyncio.Lock pour forcer la sérialisation...
```
Ce commentaire dit "on ne teste pas vraiment ce qu'on prétend tester" — c'est un aveu d'échec documenté, pas une justification acceptable.

**Pas de marqueurs pytest (`@pytest.mark`) pour catégoriser**
Impossible de lancer uniquement les tests lents, les tests d'intégration, ou les tests qui nécessitent des services externes. En CI, tout ou rien.

---

## 5. NOTE GLOBALE — 4/10

29 tests qui passent en 4 secondes sur un projet SaaS en production. **C'est insuffisant.** Le cœur du produit (restauration IA, file de jobs, stockage B2, paiement end-to-end) n'est pas testé. Les tests d'atomicité donnent une fausse confiance sur un comportement critique. La suite actuelle détecterait une régression sur l'auth et les crédits basiques — c'est tout.

---

## 6. TOP 5 PROBLÈMES

### 🔴 P0 — #1 : Les tests d'atomicité ne testent pas l'atomicité

**Sévérité : Critique / Trompeur**

```python
lock = asyncio.Lock()
async def worker():
    async with lock:  # Sérialisation Python pure
        return await consommer_credit(...)
results = await asyncio.gather(*(worker() for _ in range(20)))
```

Ce code force l'exécution **séquentielle**. Il est **mathématiquement impossible** qu'il échoue, quelle que soit l'implémentation de `consommer_credit`. Même si la fonction ne faisait aucun verrouillage DB, ce test passerait. Il ne prouve rien sur la sécurité en production PostgreSQL avec des connexions concurrentes réelles. Un bug de race condition critique en prod passerait inaperçu.

**Impact** : Fausse confiance sur le comportement le plus dangereux financièrement (double dépense de crédits).

---

### 🔴 P0 — #2 : `checkout.session.completed` n'est pas testé end-to-end

**Sévérité : Critique / Financier**

L'événement Stripe qui déclenche le crédit des utilisateurs après paiement n'est pas testé. Le seul webhook testé (`charge.succeeded`) est vraisemblablement dans le branch "non géré" du handler. On ne sait pas si :
- Un paiement réussi crédite effectivement l'utilisateur
- Le bon nombre de crédits est attribué
- L'idempotence fonctionne pour cet event spécifique
- Un `metadata` malformé n'ouvre pas une faille

**Impact** : Un bug dans ce handler signifie des paiements sans crédits (perte client) ou des crédits sans paiement (perte financière).

---

### 🔴 P0 — #3 : Aucun test positif avec token Clerk valide

**Sévérité : Critique / Sécurité**

`test_auth.py` teste uniquement les rejections. Il n'existe **aucun test** qui vérifie qu'un token Clerk valide donne accès aux endpoints. Conséquences :
- Si la logique de vérification JWKS est cassée et rejette **tous** les tokens, les 8 tests d'auth passent quand même
- Si un middleware intercepte avant Clerk et autorise par défaut, les tests ne le détectent pas

La suite de tests actuelle est compatible avec une application où **personne ne peut jamais se connecter**.

---

### 🔴 P1 — #4 : `asyncio.run(init_db())` au niveau module dans test_stripe.py

**Sévérité : Haute / Fiabilité CI**

```python
# test_stripe.py ligne 36
asyncio.run(init_db())
```

Problèmes :
1. Exécuté à l'import, **avant** la configuration de pytest-asyncio
2. Crée une nouvelle event loop, puis la ferme — si pytest-asyncio a déjà créé la sienne, conflit
3. La DB initialisée est l'application réelle (SQLite fichier ?), partagée entre tous les runs CI
4. Aucun teardown → accumulation de données entre les runs

En Python 3.12+, `asyncio.run()` dans un contexte où une loop existe déjà lève `RuntimeError`. Ce test est un accident en attente.

---

### 🟡 P1 — #5 : Tests Stripe couplés à `STRIPE_WEBHOOK_SECRET` sans mock

**Sévérité : Haute / Portabilité**

```python
from app.config import STRIPE_WEBHOOK_SECRET
# ...
signature = _generer_signature_stripe(corps)  # Utilise STRIPE_WEBHOOK_SECRET
```

Si `STRIPE_WEBHOOK_SECRET` n'est pas défini en CI (secrets non configurés, nouveau dev qui clone le repo), les tests :
- Échouent à l'import avec `AttributeError` ou utilisent `None`
- La signature générée ne correspond pas à celle attendue par le handler
- `test_webhook_stripe_evenement_valide` retourne 400 au lieu de 200

Pas de valeur par défaut documentée, pas de skip conditionnel, pas de mock. Résultat : les tests Stripe sont silencieusement inutilisables hors de l'environnement de développement initial.

---

## 7. TESTS MANQUANTS — CRITIQUES

### Auth & Sécurité
```python
# 1. Token valide → accès accordé (le test le plus basique qui manque)
def test_user_me_avec_token_valide():
    # Mock Clerk JWKS, générer un JWT RS256 valide
    token = generer_jwt_test_clerk(user_id="user_123")
    res = client.get("/api/user/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["clerk_id"] == "user_123"

# 2. Token expiré → 401 (différent de "invalide")
def test_user_me_token_expire():
    token = generer_jwt_test_clerk(exp=time.time() - 3600)
    res = client.get("/api/user/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    # Vérifier que le message indique l'expiration, pas juste "invalide"

# 3. JWKS endpoint indisponible → comportement défini
def test_auth_jwks_indisponible():
    with mock.patch("app.auth.fetch_jwks", side_effect=httpx.TimeoutException):
        res = client.get("/api/user/me", headers={"Authorization": "Bearer token"})
        assert res.status_code in (401, 503)  # Pas de 500 non géré
```

### Pipeline Métier Core
```python
# 4. Flux complet restauration (le test le plus important absent)
async def test_pipeline_restauration_complet():
    # Setup : utilisateur avec crédits
    # Upload image → POST /api/analyze
    # Lancer restauration → POST /api/restore  
    # Vérifier job ARQ créé
    # Simuler completion du job worker
    # Vérifier image disponible en B2
    # Vérifier crédit consommé
    # Vérifier réponse finale

# 5. File ARQ : job créé et traité correctement
async def test_arq_job_restauration():
    with mock.patch("app.workers.restaurer_image") as mock_worker:
        mock_worker.return_value = {"url": "https://b2.example.com/restored.jpg"}
        result = await restaurer_image_worker(ctx, photo_id="photo_123", user_id="user_1")
        assert result["url"].startswith("https://")
        # Vérifier que le crédit a été consommé
        # Vérifier que l'URL est stockée en DB
```

### Stripe End-to-End
```python
# 6. checkout.session.completed → utilisateur crédité
def test_webhook_checkout_session_completed():
    user_id = creer_utilisateur_test()
    eid = _event_id("evt_checkout")
    payload = {
        "id": eid,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_xxx",
                "payment_status": "paid",
                "metadata": {
                    "user_id": str(user_id),
                    "pack": "10_credits"
                },
                "amount_total": 999,
            }
        }
    }
    corps = json.dumps(payload).encode()
    signature = _generer_signature_stripe(corps)
    
    res = client.post("/api/stripe/webhook", content=corps,
                      headers={"Stripe-Signature": signature})
    assert res.status_code == 200
    
    # La vérification critique : les crédits ont-ils été attribués ?
    infos = asyncio.run(obtenir_credits_restants(user_id))
    assert infos["credits"] == 10

# 7. Idempotence checkout.session.completed (double livraison Stripe)
def test_webhook_checkout_idempotence_credits():
    # Envoyer 2x le même checkout.session.completed
    # Vérifier que les crédits ne sont ajoutés qu'une seule fois
    ...
```

### Concurrence Réelle
```python
# 8. Atomicité réelle avec PostgreSQL (test d'intégration)
@pytest.mark.integration  # Nécessite PostgreSQL
async def test_double_depense_concurrente_postgresql():
    """
    Deux coroutines sans Lock qui appellent consommer_credit simultanément.
    Avec FOR UPDATE, une seule doit réussir si 1 crédit restant.
    C'est le seul test qui valide réellement la sécurité en production.
    """
    uid = await creer_utilisateur_test_pg()
    await crediter_utilisateur(uid, 1)
    
    # PAS de Lock — on veut tester la concurrence réelle
    results = await asyncio.gather(
        consommer_credit(uid, "restauration", "job_1"),
        consommer_credit(uid, "restauration", "job_2"),
    )
    
    succes = [r for r in results if r["succes"]]
    assert len(succes) == 1, "Double dépense détectée !"
```

### Cas Limites Manquants
```python
# 9. crediter_utilisateur avec montant négatif ou nul
async def test_crediter_montant_invalide():
    with pytest.raises((ValueError, Exception)):
        await crediter_utilisateur(uid, -5)

# 10. Utilisateur inexistant dans consommer_credit
async def test_consommer_credit_utilisateur_inexistant():
    res = await consommer_credit(99999, "restauration", "job_x")
    # Doit retourner succes=False ou lever une exception définie, pas un 500

# 11. /api/stats avec X-Admin-Key valide
def test_stats_avec_admin_key_valide():
    res = client.get("/api/stats", headers={"X-Admin-Key": ADMIN_KEY})
    assert res.status_code == 200
    data = res.json()
    assert "utilisateurs" in data

# 12. Création automatique utilisateur au premier appel Clerk
def test_creation_utilisateur_premier_login():
    # Un clerk_id inconnu en DB doit créer le profil automatiquement
    ...
```

---

## 8. RECOMMANDATIONS — PLAN D'ACTION

### P0 — Immédiat (avant toute mise en production)

**P0-A : Créer un `conftest.py` avec infrastructure partagée et mock Clerk**
```python
# tests/conftest.py
import pytest
from unittest import mock
from cryptography.hazmat.primitives.asymmetric import rsa

@pytest.fixture(scope="session")
def clerk_rsa_keypair():
    """Génère une paire RSA pour signer les JWT de test."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()

@pytest.fixture
def token_clerk_valide(clerk_rsa_keypair):
    """Génère un JWT Clerk valide signé avec la clé de test."""
    private_key, _ = clerk_rsa_keypair
    # Signer un JWT RS256 avec les claims Clerk attendus
    ...

@pytest.fixture(autouse=True)  
def mock_clerk_jwks(clerk_rsa_keypair):
    """Intercepte les appels JWKS pour retourner la clé publique de test."""
    _, public_key = clerk_rsa_keypair
    with mock.patch("app.auth.get_public_key", return_value=public_key):
        yield
```

**P0-B : Supprimer les tests d'atomicité avec Lock et les remplacer par des tests honnêtes**

Deux options :
1. Tests unitaires qui vérifient la **logique métier séquentielle** (sans prétendre tester la concurrence)
2. Tests d'intégration PostgreSQL avec `testcontainers-python` pour tester la vraie concurrence

Supprimer `test_consommer_credit_atomique`, `test_atomicite_haute_concurrence`, `test_atomicite_credit_plus_essai` dans leur forme actuelle. Ils sont activement trompeurs.

**P0-C : Écrire le test `checkout.session.completed` end-to-end**

C'est le test financièrement le plus critique. Doit vérifier que la chaîne complète — webhook reçu → signature validée → event non dupliqué → crédits attribués → utilisateur crédité en DB — fonctionne.

---

### P1 — Cette semaine

**P1-A : Corriger `asyncio.run(init_db())` dans test_stripe.py**
```python
# Remplacer par une fixture pytest-asyncio
@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialiser_db():
    await init_db()
    yield
    # teardown si nécessaire
```

**P1-B : Supprimer les variables globales dans les fixtures de test_credits.py**
```python
# Remplacer _engine/_test_factory globaux par des fixtures propres
@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

**P1-C : Externaliser les constantes magiques**
```python
# tests/constants.py
ESSAIS_GRATUITS_DEFAUT = 3  # Synchronisé avec app/config.py
CREDITS_PACK_BASE = 10
```

**P1-D : Ajouter `pytest.ini` avec marqueurs**
```ini
[pytest]
markers =
    integration: nécessite PostgreSQL et Redis
    slow: > 1 seconde
    stripe: nécessite STRIPE_WEBHOOK_SECRET
asyncio_mode = auto
```

---

### P2 — Ce mois

**P2-A : Tests du worker ARQ**
Mocker Redis/ARQ, vérifier que les jobs sont enqueués et traités correctement.

**P2-B : Tests B2 avec mock S3**
Utiliser `moto` ou un mock S3 local pour tester les uploads/downloads sans dépendance réseau.

**P2-C : Tests de charge crédits avec PostgreSQL réel**
Utiliser `testcontainers-python` pour spawner un PostgreSQL éphémère en CI et tester l'atomicité `FOR UPDATE` réelle.

**P2-D : Couverture de code**
Ajouter `pytest-cov` et exiger un minimum de 80% sur `app/db/queries.py`, `app/services/credits.py`, `app/routes/stripe.py`. Actuellement, la couverture réelle est probablement < 30% sur le code métier.

```bash
# Ajouter au CI
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

---

## SYNTHÈSE

| Dimension | Note | Problème principal |
|-----------|------|--------------------|
| Couverture fonctionnelle | 4/10 | Pipeline core non testé, auth positive absente |
| Qualité des tests | 5/10 | Tests d'atomicité tautologiques, assertions fragiles |
| Fiabilité | 4/10 | DB partagée, `asyncio.run` module-level, timestamps réels |
| Maintenabilité | 5/10 | Pas de conftest, globaux mutables, duplication |
| **GLOBAL** | **4/10** | Suite insuffisante pour un SaaS en production |

**Le danger principal** : cette suite donne l'impression que l'application est testée alors que ses comportements les plus critiques financièrement (paiement → crédit, double dépense concurrente) ne sont pas couverts ou sont couverts par des tests qui ne peuvent pas échouer.