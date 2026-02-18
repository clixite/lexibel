# LexiBel — GDPR & AI Act EU Compliance Documentation

## 1. REGISTRE DES TRAITEMENTS (GDPR Art. 30)

### 1.1 Responsable du traitement
- **Identité**: Cabinet d’avocats utilisant LexiBel (configuré par tenant)
- **Rôle**: Responsable du traitement (Art. 4(7) GDPR)
- **DPO**: À désigner par chaque cabinet

### 1.2 Sous-traitants LLM

| Provider | Pays | Résidence données | DPA | Tier | Données autorisées | Base légale transfert |
|----------|------|-------------------|-----|------|--------------------|-----------------------|
| Mistral AI | France (EU) | 100% France | ✅ Signé | 1 | Toutes | Aucun transfert (EU-native) |
| Google Gemini | Belgique (EU) | europe-west1 (Saint-Ghislain) | ✅ Google Cloud DPA | 1 | Toutes | Aucun transfert (EU) |
| Anthropic | USA | US (EU-US DPF) | ✅ Signé | 1 | Toutes | Décision d’adéquation EU-US DPF (10/07/2023) |
| OpenAI | USA / EU (Azure) | US ou EU | ✅ Signé | 1 | Toutes | Décision d’adéquation EU-US DPF (10/07/2023) |
| DeepSeek | Chine | Chine | ❌ | 2 | Anonymisées uniquement | Art. 49(1)(a) GDPR + anonymisation |
| GLM-4 (Zhipu AI) | Chine | Chine | ❌ | 3 | Publiques uniquement | Pas de données personnelles transférées |
| Kimi (Moonshot AI) | Chine | Chine | ❌ | 3 | Publiques uniquement | Pas de données personnelles transférées |

### 1.3 Catégories de données traitées
- Données d’identification (noms, NISS, adresses)
- Données financières (IBAN, BCE/TVA)
- Données judiciaires (Art. 10 GDPR — dossiers, jugements)
- Données de santé (si pertinentes au dossier — Art. 9 GDPR)
- Données relatives aux mineurs
- Jurisprudence publiée et doctrine (données publiques)

### 1.4 Finalités du traitement
- Analyse de dossiers juridiques
- Rédaction de documents juridiques
- Recherche juridique
- Traduction juridique
- Résumé de documents

### 1.5 Durée de conservation
- **Logs d’audit IA**: 5 ans (prescription légale en Belgique)
- **Contenu des prompts/réponses**: NON stocké (secret professionnel Art. 458 C.P.)
- **Mapping d’anonymisation**: NON persisté (mémoire uniquement, perdu à la fin de la requête)
- **Clés API**: Chiffrées AES-256 en base de données

---

## 2. DPIA — Data Protection Impact Assessment (GDPR Art. 35)

### 2.1 Description du traitement
**Système**: LexiBel — Practice Management System avec IA intégrée
**Classification AI Act**: Système IA à HAUT RISQUE (Annexe III, point 8 — administration de la justice)

Le traitement consiste à envoyer des extraits de documents juridiques à des modèles de langage (LLM) pour obtenir des analyses, résumés, ou brouillons. Les données peuvent contenir des informations personnelles de clients, parties adverses et témoins.

### 2.2 Nécessité et proportionnalité
- **Nécessité**: L’IA permet aux avocats de traiter plus efficacement les dossiers complexes
- **Proportionnalité**: Seuls les extraits nécessaires sont envoyés, pas les dossiers complets
- **Minimisation**: Classification automatique et anonymisation avant transfert

### 2.3 Risques identifiés

| Risque | Probabilité | Impact | Score |
|--------|-------------|--------|-------|
| Transfert de données sensibles vers juridiction non-EU | Faible (grâce au routing automatique) | Élevé | Moyen |
| Ré-identification de données anonymisées | Très faible | Élevé | Faible |
| Hallucination IA dans contexte juridique | Moyenne | Élevé | Moyen |
| Accès non autorisé aux logs d’audit | Faible (RLS + RBAC) | Moyen | Faible |
| Violation du secret professionnel | Très faible (contenu non stocké) | Très élevé | Faible |

### 2.4 Mesures d’atténuation

| Mesure | Risque couvert | Implémentation |
|--------|----------------|----------------|
| Classification automatique (4 niveaux) | Transfert non autorisé | `DataClassifier` — regex + heuristiques locales |
| Routing par tier | Transfert non autorisé | `LLMGateway._select_provider()` |
| Anonymisation automatique | Transfert données personnelles | `DataAnonymizer.anonymize()` |
| Vérification post-anonymisation | Fuite de données | `DataAnonymizer.verify_anonymization()` |
| Blocage si anonymisation échoue | Transfert non autorisé | Gateway bloque l’envoi |
| Hash-only storage | Secret professionnel | SHA-256 des prompts/réponses, pas le contenu |
| Human-in-the-loop | Hallucination IA | Flag `require_human_validation` |
| RLS + RBAC | Accès non autorisé | PostgreSQL RLS + middleware RBAC |
| Audit trail complet | Traçabilité | Table `ai_audit_logs` (append-only) |
| Principe de précaution | Classification insuffisante | Défaut = SENSITIVE si aucune entité détectée |

### 2.5 Risque résiduel
**FAIBLE** — avec toutes les mesures actives, le risque résiduel est acceptable.

---

## 3. AI ACT EU — Matrice de conformité (Règlement 2024/1689)

| Article | Exigence | Implémentation LexiBel | Preuve | Status |
|---------|----------|------------------------|--------|--------|
| Art. 6 + Annexe III | Classification haut risque | LexiBel classifié HIGH-RISK (administration de la justice) | Documentation système | ✅ |
| Art. 9 | Système de gestion des risques | DPIA + classification automatique + routing par tier | `data_classifier.py`, `gateway.py` | ✅ |
| Art. 11 | Documentation technique | Ce document + code source documenté | `GDPR_AI_COMPLIANCE.md` | ✅ |
| Art. 13 | Transparence et information | Logging de chaque interaction IA + badges UI | `audit_logger.py`, frontend badges | ✅ |
| Art. 14 | Contrôle humain | Human-in-the-loop flag + validation manuelle | `human_validated` field + UI button | ✅ |
| Art. 15 | Exactitude, robustesse, cybersécurité | TLS 1.3, AES-256, RBAC, RLS, red team tests | `test_llm_security.py` | ✅ |
| Art. 17 | Système de gestion de la qualité | Stats d’utilisation + monitoring + alertes | `/audit/stats` endpoint | ✅ |
| Art. 26 | Obligations du déployeur | Information client + procédure validation | Politique d’utilisation IA (§4) | ✅ |
| Art. 50 | Transparence envers l’utilisateur | Badge "Réponse générée par IA" sur chaque réponse | Frontend Hub IA | ✅ |

---

## 4. POLITIQUE D’UTILISATION IA — Template pour cabinets d’avocats

### 4.1 Information client obligatoire
L’avocat DOIT informer son client de l’utilisation de l’IA dans le traitement de son dossier, conformément au:
- Règlement Obas (Ordre des Barreaux francophones et germanophone)
- AI Act EU Art. 50 (transparence)
- GDPR Art. 13 (information)

**Formulation recommandée**:
> "Notre cabinet utilise des outils d’intelligence artificielle pour assister dans l’analyse juridique et la rédaction de documents. Ces outils sont soumis à des contrôles stricts de protection des données (RGPD) et de conformité (AI Act EU). Toute production IA est systématiquement vérifiée et validée par un avocat. L’avocat reste seul responsable du travail fourni."

### 4.2 Cas d’usage autorisés
- ✅ Recherche juridique (jurisprudence, doctrine)
- ✅ Rédaction de brouillons de documents
- ✅ Résumé de documents volumineux
- ✅ Analyse de risques juridiques
- ✅ Traduction juridique
- ❌ Décision finale sur un dossier (toujours humain)
- ❌ Communication directe avec le client sans relecture
- ❌ Analyse de données de mineurs sans supervision renforcée

### 4.3 Procédure de validation humaine
1. L’avocat soumet une requête à l’IA
2. L’IA génère une réponse avec indication du provider et du niveau de sensibilité
3. L’avocat examine la réponse
4. L’avocat clique "Valider" pour confirmer (AI Act Art. 14)
5. La validation est enregistrée dans l’audit trail
6. L’avocat reste SEUL responsable du contenu final

### 4.4 Gestion des incidents
En cas de suspicion de fuite de données ou de dysfonctionnement:
1. **Signalement immédiat** au DPO du cabinet
2. **Blocage** du provider concerné via l’admin LLM
3. **Investigation** via les logs d’audit
4. **Notification** à l’APD (Autorité de Protection des Données) dans les 72h si nécessaire (Art. 33 GDPR)
5. **Documentation** de l’incident dans le registre des incidents

---

## 5. ARCHITECTURE DE SÉCURITÉ

### 5.1 Flux de données

```
Utilisateur → [Prompt]
       ↓
  DataClassifier (local, pas de LLM)
       ↓
  Classification: PUBLIC / SEMI / SENSITIVE / CRITICAL
       ↓
  Route Selector (tier + coût + préférence)
       ↓
  [Si non-EU provider + données non-PUBLIC]
       ↓
  DataAnonymizer → verify_anonymization()
       ↓ (Si échec → BLOCAGE)
       ↓
  LLM Provider API call (TLS 1.3)
       ↓
  [Si anonymisé] → Dé-anonymisation
       ↓
  AI Audit Logger (hash only, pas de contenu)
       ↓
  Réponse à l’utilisateur (avec badges provider + sensibilité)
```

### 5.2 Fallback chains

| Sensibilité | Chain | Condition |
|-------------|-------|-----------|
| CRITICAL | Mistral → Gemini → STOP | Jamais Tier 2-3 |
| SENSITIVE | Mistral → Gemini → Anthropic → OpenAI → STOP | Tier 1 uniquement |
| SEMI | Best price Tier 1 → DeepSeek (anonymisé) → STOP | Anonymisation obligatoire Tier 2 |
| PUBLIC | Best price all tiers → fallback chain complète | Aucune restriction |

### 5.3 Tests de sécurité (Red Team)
Fichier: `apps/api/tests/test_llm_security.py`

Tous les tests suivants DOIVENT passer pour autoriser le déploiement:
- Données CRITICAL jamais envoyées aux providers Tier 2-3
- Anonymisation supprime toutes les entités détectées
- Échec d’anonymisation bloque la requête
- Roundtrip anonymisation/dé-anonymisation identique
- Logs d’audit créés pour chaque requête
- Logs ne contiennent JAMAIS le contenu
- Fallback respecte les tiers
- Classification par défaut = SENSITIVE
- Providers chinois ne reçoivent JAMAIS de données non vérifiées

---

## 6. CONTACTS ET RÉFÉRENCES

### Autorités
- **APD Belgique**: Autorité de Protection des Données — https://www.autoriteprotectiondonnees.be
- **AI Office EU**: Bureau européen de l’IA — superviseur AI Act

### Textes légaux
- GDPR: Règlement (UE) 2016/679
- AI Act: Règlement (UE) 2024/1689
- Code Pénal belge Art. 458 (secret professionnel)
- Recommandation Avocats.be 2024 (utilisation IA par les avocats)

### Dernière mise à jour
Date: 2026-02-18
Version: 1.0
Auteur: Système automatisé LexiBel
