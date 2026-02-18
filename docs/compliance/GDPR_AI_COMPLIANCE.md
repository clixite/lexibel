# DOCUMENTATION DE CONFORMITE RGPD & AI ACT UE

## LexiBel -- Practice Management System pour avocats belges
## Module: LLM Gateway (Passerelle d'Intelligence Artificielle)

---

**Version du document:** 1.0
**Date de creation:** 2026-02-18
**Derniere mise a jour:** 2026-02-18
**Classification:** CONFIDENTIEL -- RESERVE AUX RESPONSABLES DU TRAITEMENT
**Redige par:** Clixite SRL (sous-traitant technique)
**A valider par:** Le DPO du cabinet, le Batonnier competent

---

## TABLE DES MATIERES

1. [Registre des traitements (RGPD Art. 30)](#1-registre-des-traitements-rgpd-art-30)
2. [Analyse d'impact (DPIA) -- RGPD Art. 35](#2-analyse-dimpact-dpia--rgpd-art-35)
3. [Transferts internationaux (RGPD Art. 44-49)](#3-transferts-internationaux-rgpd-art-44-49)
4. [AI Act UE -- Checklist de conformite (Reglement 2024/1689)](#4-ai-act-ue--checklist-de-conformite-reglement-20241689)
5. [Secret professionnel belge](#5-secret-professionnel-belge)
6. [Annexes](#6-annexes)

---

## PREAMBULE

Le present document constitue la documentation de conformite du module **LLM Gateway** integre au systeme **LexiBel**, un Practice Management System destine aux cabinets d'avocats belges.

Ce module permet aux avocats d'utiliser des modeles de langage (LLM) pour assister leur travail juridique, tout en garantissant le respect des obligations suivantes :

- **Reglement (UE) 2016/679** (RGPD) -- protection des donnees a caractere personnel
- **Reglement (UE) 2024/1689** (AI Act) -- regulation de l'intelligence artificielle
- **Article 458 du Code penal belge** -- secret professionnel
- **Reglement de l'Orde van Vlaamse Balies (Obas)** et **recommandations d'Avocats.be** -- deontologie des avocats
- **Loi du 30 juillet 2018** relative a la protection des personnes physiques a l'egard des traitements de donnees a caractere personnel (transposition belge du RGPD)

**AVERTISSEMENT :** Ce document ne constitue pas un avis juridique. Chaque cabinet d'avocats, en tant que responsable du traitement, doit valider cette documentation avec son Delegue a la Protection des Donnees (DPO) et, le cas echeant, avec l'Autorite de Protection des Donnees (APD/GBA).

---

## 1. REGISTRE DES TRAITEMENTS (RGPD Art. 30)

En application de l'article 30 du RGPD, le present registre decrit les activites de traitement liees au module LLM Gateway.

---

### 1.1 Identification des acteurs

#### 1.1.1 Responsable du traitement

| Champ | Description |
|-------|-------------|
| **Identite** | Le cabinet d'avocats (tenant) utilisant LexiBel |
| **Qualite** | Responsable du traitement au sens de l'Art. 4(7) RGPD |
| **Fondement** | Le cabinet determine les finalites et les moyens du traitement des donnees de ses clients |
| **Obligations** | Art. 24 RGPD -- mise en oeuvre de mesures techniques et organisationnelles appropriees |
| **DPO** | A designer par chaque cabinet conformement a l'Art. 37 RGPD si les conditions sont remplies |

> **Note :** En architecture multi-tenant, chaque cabinet constitue un responsable du traitement distinct. Il n'existe aucune responsabilite conjointe (Art. 26 RGPD) entre les cabinets.

#### 1.1.2 Sous-traitant

| Champ | Description |
|-------|-------------|
| **Identite** | Clixite SRL |
| **Qualite** | Sous-traitant au sens de l'Art. 4(8) RGPD |
| **Numero d'entreprise** | [A completer] |
| **Siege social** | [A completer -- Belgique] |
| **Role** | Developpeur et operateur de la plateforme LexiBel, y compris le module LLM Gateway |
| **Contrat Art. 28** | Un contrat de sous-traitance conforme a l'Art. 28 RGPD lie Clixite SRL a chaque cabinet |
| **Garanties** | Clixite SRL s'engage a ne traiter les donnees que sur instruction documentee du responsable du traitement |

#### 1.1.3 Sous-sous-traitants (Fournisseurs LLM)

Conformement a l'Art. 28(2) et 28(4) RGPD, Clixite SRL fait appel aux sous-sous-traitants suivants pour le traitement des requetes LLM :

| # | Fournisseur | Siege social | Modele(s) | Juridiction hebergement | Adequation RGPD | Tier |
|---|-------------|-------------|-----------|------------------------|-----------------|------|
| 1 | **Mistral AI** | Paris, France | Mistral Large, Mistral Medium, Mistral Small | Union europeenne (France) | Adequate -- droit UE | **Tier 1** |
| 2 | **Anthropic** | San Francisco, USA | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku | USA (EU-US Data Privacy Framework) | Adequate -- Decision d'adequation EU-US DPF (10/07/2023) | **Tier 1** |
| 3 | **OpenAI** | San Francisco, USA | GPT-4, GPT-4 Turbo, GPT-4o | USA (EU-US Data Privacy Framework) | Adequate -- Decision d'adequation EU-US DPF (10/07/2023) | **Tier 1** |
| 4 | **DeepSeek** | Hangzhou, Chine | DeepSeek-V3, DeepSeek-R1 | Chine (RPC) | **Non adequate** -- Pas de decision d'adequation Art. 45 | **Tier 2** |
| 5 | **Zhipu AI** | Pekin, Chine | GLM-4 | Chine (RPC) | **Non adequate** -- Pas de decision d'adequation Art. 45 | **Tier 3** |
| 6 | **Moonshot AI** | Pekin, Chine | Kimi | Chine (RPC) | **Non adequate** -- Pas de decision d'adequation Art. 45 | **Tier 3** |

> **Systeme de Tiers :**
> - **Tier 1 :** Toutes les donnees peuvent etre transmises (donnees personnelles, donnees juridiques, documents confidentiels) -- sous reserve d'anonymisation recommandee.
> - **Tier 2 :** Exclusivement des donnees **anonymisees** -- aucune donnee a caractere personnel, aucune donnee couverte par le secret professionnel.
> - **Tier 3 :** Exclusivement des donnees **publiques** -- legislation, jurisprudence publiee, doctrine publiee, questions juridiques generales sans lien avec un dossier.

---

### 1.2 Description du traitement

#### 1.2.1 Finalites du traitement

| # | Finalite | Description | Base legale |
|---|----------|-------------|-------------|
| F1 | **Aide a la redaction juridique** | Assistance a la redaction de conclusions, contrats, courriers, memos juridiques | Interet legitime (Art. 6(1)(f)) + consentement explicite du client |
| F2 | **Analyse de dossiers** | Resume, extraction d'informations cles, identification de risques juridiques dans les dossiers | Interet legitime (Art. 6(1)(f)) + consentement explicite du client |
| F3 | **Recherche juridique** | Recherche de jurisprudence, analyse de legislation, veille juridique | Interet legitime (Art. 6(1)(f)) |
| F4 | **Traduction juridique** | Traduction de documents juridiques (FR/NL/DE/EN) | Interet legitime (Art. 6(1)(f)) + consentement explicite du client |
| F5 | **Audit et conformite** | Journalisation des requetes pour tracabilite deontologique | Obligation legale (Art. 6(1)(c)) -- deontologie des avocats |

#### 1.2.2 Base legale detaillee

**Interet legitime (Art. 6(1)(f) RGPD) :**

La mise en balance des interets (balancing test) a ete effectuee :

- **Interet legitime poursuivi :** Amelioration de la qualite et de l'efficacite des services juridiques rendus aux clients.
- **Necessite du traitement :** L'utilisation de LLM permet un gain de productivite significatif et une amelioration de la qualite redactionnelle, au benefice direct du client.
- **Mise en balance avec les droits des personnes concernees :** Les mesures d'attenuation mises en oeuvre (classification, anonymisation, routing par tier, chiffrement) reduisent le risque a un niveau acceptable. Les personnes concernees s'attendent raisonnablement a ce que leur avocat utilise des outils modernes pour traiter leur dossier.

**Consentement explicite du client (Art. 6(1)(a) et Art. 9(2)(a) RGPD) :**

- Le consentement du client est requis **avant** toute transmission de donnees a un LLM.
- Ce consentement est **specifique** (par type de traitement), **eclaire** (information sur les fournisseurs et les risques), **libre** (possibilite de refuser sans prejudice) et **univoque** (acte positif clair).
- Le consentement est **documentable** et **revocable** a tout moment (Art. 7 RGPD).
- Pour les **donnees sensibles** (Art. 9 RGPD), le consentement doit etre **explicite**.

#### 1.2.3 Donnees traitees

| Categorie | Type de donnees | Sensibilite | Classification LexiBel |
|-----------|----------------|-------------|----------------------|
| **Documents juridiques** | Conclusions, requetes, contrats, memos, avis juridiques | Elevee -- secret professionnel | `CONFIDENTIAL` |
| **Correspondance** | E-mails, courriers, notes d'entretien | Elevee -- secret professionnel | `CONFIDENTIAL` |
| **Donnees d'identification** | Noms, adresses, numeros de registre national, numeros d'entreprise | Donnees personnelles | `PERSONAL` |
| **Donnees judiciaires** | Numeros de role, decisions de justice (non publiees), PV d'audition | Elevee -- Art. 10 RGPD | `RESTRICTED` |
| **Donnees de sante** | Le cas echeant, dans les dossiers de droit medical ou social | Tres elevee -- Art. 9 RGPD | `RESTRICTED` |
| **Donnees financieres** | Releves, comptes de tiers, etats de frais | Elevee | `CONFIDENTIAL` |
| **Donnees publiques** | Legislation, jurisprudence publiee, doctrine | Faible | `PUBLIC` |

#### 1.2.4 Categories de personnes concernees

| Categorie | Description | Droits specifiques |
|-----------|-------------|-------------------|
| **Clients du cabinet** | Personnes physiques ou morales representees par l'avocat | Droits RGPD complets + droit a l'information renforcee |
| **Parties adverses** | Personnes physiques ou morales en litige avec le client | Droits RGPD complets -- information via l'avocat adverse |
| **Temoins** | Personnes mentionnees dans les dossiers | Droits RGPD complets |
| **Magistrats et fonctionnaires** | Dans le cadre de decisions ou correspondances administratives | Droits RGPD dans la mesure applicable |
| **Tiers mentionnes** | Toute personne physique identifiable dans les documents traites | Droits RGPD complets |

#### 1.2.5 Duree de conservation

| Type de donnees | Duree de conservation | Fondement |
|----------------|----------------------|-----------|
| **Logs d'audit des requetes LLM** | **5 ans** a compter de la requete | Prescription de droit commun belge (Art. 2262bis C. civ.) -- responsabilite contractuelle |
| **Prompts et reponses (cache)** | **30 jours** maximum (cache technique) | Necessite technique -- optimisation des performances |
| **Donnees d'anonymisation** | **Duree du dossier** + 5 ans | Alignement sur la conservation des dossiers d'avocats |
| **Consentements des clients** | **Duree de la relation** + 10 ans | Preuve du consentement (Art. 7(1) RGPD) + prescription |
| **Metriques agregees (anonymes)** | **Illimitee** | Donnees non personnelles apres anonymisation irreversible |

#### 1.2.6 Mesures de securite (Art. 32 RGPD)

**Mesures techniques :**

| Mesure | Description | Implementation |
|--------|-------------|----------------|
| **Classification automatique** | Chaque document/prompt est classe automatiquement selon sa sensibilite (`PUBLIC`, `PERSONAL`, `CONFIDENTIAL`, `RESTRICTED`) | Modele de classification NLP en local avant envoi |
| **Anonymisation (PII Stripping)** | Suppression ou pseudonymisation des donnees a caractere personnel avant envoi aux LLM Tier 2 | Moteur NER (Named Entity Recognition) + regles regex pour NISS, numeros BCE, IBAN |
| **Routing intelligent** | Acheminement automatique des requetes vers le fournisseur LLM approprie selon le tier de classification | Middleware de routage avec matrice classification/tier |
| **Chiffrement en transit** | TLS 1.3 pour toutes les communications avec les fournisseurs LLM | Certificats geres, epinglage de certificats (certificate pinning) |
| **Chiffrement au repos** | AES-256 pour les logs d'audit et les donnees en cache | Cles gerees par HSM ou equivalent |
| **Isolation multi-tenant** | Separation stricte des donnees entre cabinets | Schema de base de donnees isole par tenant, cles de chiffrement distinctes |
| **Audit trail immutable** | Journalisation de chaque requete LLM avec horodatage, utilisateur, classification, fournisseur, hash du prompt | Logs append-only, signes cryptographiquement |

**Mesures organisationnelles :**

| Mesure | Description |
|--------|-------------|
| **Formation des utilisateurs** | Chaque avocat recoit une formation sur l'utilisation appropriee du LLM Gateway et les risques associes |
| **Politique d'utilisation acceptable** | Document definissant les usages autorises et interdits du module LLM |
| **Procedure de gestion des incidents** | Notification a l'APD dans les 72h (Art. 33 RGPD) et aux personnes concernees (Art. 34 RGPD) |
| **Revue periodique** | Audit annuel des sous-sous-traitants et de leurs garanties |
| **Contrats Art. 28** | Contrats de sous-traitance avec chaque fournisseur LLM |

---

### 1.3 Destinataires des donnees

| Destinataire | Type | Donnees transmises | Base de la transmission |
|-------------|------|-------------------|----------------------|
| **Mistral AI** | Sous-sous-traitant | Toutes categories (Tier 1) | Contrat Art. 28 RGPD |
| **Anthropic** | Sous-sous-traitant | Toutes categories (Tier 1) | Contrat Art. 28 RGPD + EU-US DPF |
| **OpenAI** | Sous-sous-traitant | Toutes categories (Tier 1) | Contrat Art. 28 RGPD + EU-US DPF |
| **DeepSeek** | Sous-sous-traitant | Donnees anonymisees uniquement (Tier 2) | Contrat Art. 28 RGPD + CCT (Art. 46(2)(c)) |
| **Zhipu AI** | Sous-sous-traitant | Donnees publiques uniquement (Tier 3) | Contrat Art. 28 RGPD + CCT (Art. 46(2)(c)) |
| **Moonshot AI** | Sous-sous-traitant | Donnees publiques uniquement (Tier 3) | Contrat Art. 28 RGPD + CCT (Art. 46(2)(c)) |

---

## 2. ANALYSE D'IMPACT (DPIA) -- RGPD Art. 35

### 2.1 Obligation de realiser une DPIA

L'analyse d'impact relative a la protection des donnees est **obligatoire** pour le traitement decrit, pour les raisons suivantes :

- [x] **Art. 35(1) RGPD :** Le traitement est susceptible d'engendrer un risque eleve pour les droits et libertes des personnes physiques.
- [x] **Art. 35(3)(a) RGPD :** Evaluation systematique et approfondie d'aspects personnels (profilage juridique des dossiers).
- [x] **Art. 35(3)(b) RGPD :** Traitement a grande echelle de categories particulieres de donnees (donnees judiciaires, Art. 10 RGPD ; le cas echeant, donnees de sante, Art. 9 RGPD).
- [x] **Lignes directrices du WP29/EDPB :** Combinaison de criteres (nouvelles technologies, donnees sensibles, personnes vulnerables, grande echelle).
- [x] **Liste de l'APD belge :** Traitements utilisant l'intelligence artificielle pour prendre des decisions affectant les personnes concernees.

---

### 2.2 Description systematique du traitement

#### 2.2.1 Nature du traitement

Le module LLM Gateway constitue une **passerelle d'intelligence artificielle** qui :

1. **Recoit** des requetes (prompts) de l'avocat utilisateur, contenant potentiellement des donnees a caractere personnel et des informations couvertes par le secret professionnel.
2. **Classifie** automatiquement la sensibilite des donnees contenues dans le prompt.
3. **Anonymise** les donnees a caractere personnel si la classification l'exige (pour les fournisseurs Tier 2).
4. **Route** la requete vers le fournisseur LLM approprie en fonction de la classification.
5. **Transmet** le prompt au fournisseur LLM via une API securisee (TLS 1.3).
6. **Recoit** la reponse du fournisseur LLM.
7. **Re-identifie** les donnees anonymisees dans la reponse (le cas echeant, pour les requetes Tier 2).
8. **Presente** la reponse a l'avocat utilisateur.
9. **Journalise** l'ensemble de la transaction dans un log d'audit immutable.

#### 2.2.2 Portee du traitement

| Aspect | Detail |
|--------|--------|
| **Volume** | Potentiellement plusieurs milliers de requetes par jour, par cabinet |
| **Frequence** | Continue (disponible 24h/24, 7j/7) |
| **Zone geographique** | Belgique (utilisateurs) ; UE, USA, Chine (fournisseurs) |
| **Nombre de personnes concernees** | Potentiellement plusieurs milliers par cabinet (clients, parties adverses, temoins) |

#### 2.2.3 Contexte du traitement

- **Relation avec les personnes concernees :** Les personnes concernees sont principalement les clients du cabinet (relation de confiance renforcee) et les parties adverses (aucune relation directe).
- **Controle des personnes concernees :** Les personnes concernees n'ont aucun controle direct sur le traitement. L'avocat agit comme intermediaire.
- **Attentes raisonnables :** Les clients s'attendent a ce que leur avocat utilise des outils modernes, mais pas necessairement a ce que leurs donnees soient transmises a des fournisseurs d'IA, en particulier hors de l'UE.
- **Desequilibre de pouvoir :** Il existe un desequilibre inherent entre l'avocat (et ses outils) et les personnes concernees, en particulier les parties adverses.

---

### 2.3 Evaluation de la necessite et de la proportionnalite

#### 2.3.1 Necessite (Art. 35(7)(b) RGPD)

| Critere | Evaluation |
|---------|-----------|
| **Le traitement est-il necessaire a la finalite ?** | Oui. L'utilisation de LLM ameliore significativement la qualite et l'efficacite du travail juridique. |
| **Existe-t-il des alternatives moins intrusives ?** | Partiellement. Un LLM deploye localement (on-premise) eviterait les transferts, mais les performances actuelles des modeles locaux sont insuffisantes pour un usage juridique professionnel. L'architecture par tiers constitue le compromis optimal. |
| **Le traitement est-il proportionnel a la finalite ?** | Oui, grace au systeme de classification et de routing par tiers qui limite les donnees transmises au strict necessaire pour chaque fournisseur. |

#### 2.3.2 Proportionnalite

**Principe de minimisation des donnees (Art. 5(1)(c) RGPD) :**

- L'anonymisation automatique des donnees personnelles avant envoi aux fournisseurs Tier 2 et Tier 3 garantit que seules les donnees strictement necessaires sont transmises.
- Le systeme de classification empeche l'envoi de donnees `RESTRICTED` ou `CONFIDENTIAL` aux fournisseurs Tier 2 et Tier 3.
- L'avocat conserve la maitrise : il peut choisir de ne pas soumettre certaines donnees au LLM.

**Principe de limitation de la conservation (Art. 5(1)(e) RGPD) :**

- Les donnees en cache sont supprimees apres 30 jours maximum.
- Les logs d'audit sont conserves 5 ans (alignement sur la prescription belge).
- Aucune donnee n'est conservee par les fournisseurs LLM au-dela du traitement de la requete (clause contractuelle).

---

### 2.4 Risques pour les droits et libertes des personnes concernees

#### 2.4.1 Matrice des risques

| # | Risque | Gravite | Vraisemblance | Niveau | Description |
|---|--------|---------|---------------|--------|-------------|
| R1 | **Violation du secret professionnel** | Tres elevee (4) | Faible (1) | **Eleve** | Transmission non autorisee de donnees confidentielles a un fournisseur LLM non adequat |
| R2 | **Fuite de donnees chez le fournisseur** | Tres elevee (4) | Faible (1) | **Eleve** | Breach de securite chez un fournisseur LLM exposant des donnees de clients |
| R3 | **Utilisation des donnees pour entrainement** | Elevee (3) | Moyenne (2) | **Eleve** | Un fournisseur utilise les prompts pour re-entrainer son modele, exposant potentiellement les donnees |
| R4 | **Transfert vers juridiction non adequate** | Elevee (3) | Moyenne (2) | **Eleve** | Transfert de donnees personnelles vers la Chine sans garanties suffisantes |
| R5 | **Defaillance de l'anonymisation** | Elevee (3) | Faible (1) | **Moyen** | Le moteur d'anonymisation ne detecte pas toutes les donnees personnelles |
| R6 | **Erreur de classification** | Elevee (3) | Faible (1) | **Moyen** | Un document confidentiel est classe comme public et envoye a un fournisseur Tier 3 |
| R7 | **Re-identification des donnees anonymisees** | Moyenne (2) | Faible (1) | **Faible** | Un tiers parvient a re-identifier des donnees anonymisees a partir du contexte |
| R8 | **Acces non autorise aux logs** | Elevee (3) | Faible (1) | **Moyen** | Un employe de Clixite ou du cabinet accede aux logs sans autorisation |
| R9 | **Dependance au fournisseur (vendor lock-in)** | Faible (1) | Moyenne (2) | **Faible** | Incapacite de changer de fournisseur LLM, compromettant la qualite du service |
| R10 | **Decision juridique basee sur une hallucination IA** | Tres elevee (4) | Moyenne (2) | **Tres eleve** | L'avocat se fie a une reponse erronee du LLM, causant un prejudice au client |

**Echelle de gravite :** 1 (Faible) -- 2 (Moyenne) -- 3 (Elevee) -- 4 (Tres elevee)
**Echelle de vraisemblance :** 1 (Faible) -- 2 (Moyenne) -- 3 (Elevee) -- 4 (Tres elevee)

---

### 2.5 Mesures d'attenuation

#### 2.5.1 Mesures par risque

| Risque | Mesures d'attenuation | Risque residuel |
|--------|----------------------|-----------------|
| **R1 -- Violation du secret** | Classification automatique + routing par tiers + blocage des donnees `RESTRICTED`/`CONFIDENTIAL` vers Tier 2/3 + consentement explicite du client | **Faible** |
| **R2 -- Fuite chez le fournisseur** | Contrats Art. 28 avec clauses de securite renforcees + audit annuel des fournisseurs + notification de breach + chiffrement en transit (TLS 1.3) | **Moyen** (risque externalise) |
| **R3 -- Entrainement sur les donnees** | Clause contractuelle d'interdiction d'utilisation pour entrainement + API en mode "zero data retention" + verification technique | **Faible** |
| **R4 -- Transfert non adequate** | Fournisseurs chinois limites aux Tier 2 (anonymise) et Tier 3 (public) + CCT + mesures supplementaires (chiffrement) | **Faible** |
| **R5 -- Defaillance anonymisation** | Double verification (NER + regex) + validation humaine optionnelle + logs d'audit pour detection post-hoc + amelioration continue du moteur | **Faible** |
| **R6 -- Erreur de classification** | Modele de classification valide sur corpus juridique belge + seuil de confiance conservateur + possibilite de reclassification manuelle par l'avocat | **Faible** |
| **R7 -- Re-identification** | k-anonymite (k >= 5) + suppression des quasi-identifiants + evaluation periodique du risque de re-identification | **Tres faible** |
| **R8 -- Acces non autorise** | Controle d'acces base sur les roles (RBAC) + authentification multi-facteurs + journalisation des acces + separation des privileges | **Faible** |
| **R9 -- Vendor lock-in** | Architecture multi-fournisseurs (6 fournisseurs) + interface API abstraite + possibilite de deploiement local futur | **Tres faible** |
| **R10 -- Hallucination IA** | Avertissement systematique "verification humaine requise" + interdiction d'utilisation autonome + formation des avocats + references aux sources | **Moyen** (risque inherent aux LLM) |

#### 2.5.2 Risque residuel global

Apres application des mesures d'attenuation, le **risque residuel global** est evalue comme **ACCEPTABLE**, sous reserve de :

1. La mise en oeuvre effective de toutes les mesures techniques et organisationnelles decrites.
2. La validation du present DPIA par le DPO du cabinet.
3. La consultation prealable de l'APD si le DPO l'estime necessaire (Art. 36 RGPD).
4. La revue annuelle du present DPIA et de ses mesures d'attenuation.

---

## 3. TRANSFERTS INTERNATIONAUX (RGPD Art. 44-49)

### 3.1 Principe general

L'article 44 du RGPD dispose que tout transfert de donnees a caractere personnel vers un pays tiers ne peut avoir lieu que si les conditions du Chapitre V du RGPD sont respectees.

Le module LLM Gateway implique des transferts vers les juridictions suivantes :

| Juridiction | Decision d'adequation | Mecanisme de transfert |
|-------------|----------------------|----------------------|
| **France (UE)** | Non necessaire -- droit UE applicable | Libre circulation (Art. 1(3) RGPD) |
| **Etats-Unis** | Oui -- EU-US Data Privacy Framework (Decision d'execution (UE) 2023/1795 du 10/07/2023) | Art. 45 RGPD -- Decision d'adequation |
| **Chine (RPC)** | **Non** -- Aucune decision d'adequation | Art. 46(2)(c) RGPD -- Clauses contractuelles types (CCT) + mesures supplementaires |

---

### 3.2 Analyse par fournisseur

#### 3.2.1 Mistral AI (France, UE) -- TIER 1

| Aspect | Detail |
|--------|--------|
| **Siege** | Paris, France |
| **Hebergement des donnees** | Union europeenne (France) |
| **Mecanisme de transfert** | **Aucun transfert international** -- traitement au sein de l'UE |
| **Donnees autorisees** | Toutes categories : `PUBLIC`, `PERSONAL`, `CONFIDENTIAL`, `RESTRICTED` |
| **Clauses contractuelles** | Contrat de sous-traitance Art. 28 RGPD |
| **Garanties specifiques** | Zero data retention, pas d'entrainement sur les donnees, hebergement UE garanti |
| **Evaluation** | **Conforme** -- aucun risque lie au transfert |

#### 3.2.2 Anthropic Claude (USA, EU-US DPF) -- TIER 1

| Aspect | Detail |
|--------|--------|
| **Siege** | San Francisco, Californie, USA |
| **Hebergement des donnees** | USA (avec option de traitement en UE selon le contrat) |
| **Mecanisme de transfert** | **Decision d'adequation EU-US DPF** (Art. 45 RGPD) |
| **Certification DPF** | A verifier sur https://www.dataprivacyframework.gov/list |
| **Donnees autorisees** | Toutes categories : `PUBLIC`, `PERSONAL`, `CONFIDENTIAL`, `RESTRICTED` |
| **Clauses contractuelles** | Contrat de sous-traitance Art. 28 RGPD + DPA specifique |
| **Garanties specifiques** | Zero data retention pour les API commerciales, pas d'entrainement sur les donnees API |
| **Risques identifies** | Acces par les autorites americaines (FISA 702, EO 12333) -- attenue par le mecanisme de recours du DPF |
| **Mesures supplementaires** | Chiffrement en transit (TLS 1.3), evaluation annuelle de la certification DPF |
| **Evaluation** | **Conforme** -- sous reserve de la validite continue du DPF et de la certification d'Anthropic |

#### 3.2.3 OpenAI GPT-4 (USA, EU-US DPF) -- TIER 1

| Aspect | Detail |
|--------|--------|
| **Siege** | San Francisco, Californie, USA |
| **Hebergement des donnees** | USA (avec option Azure OpenAI en UE) |
| **Mecanisme de transfert** | **Decision d'adequation EU-US DPF** (Art. 45 RGPD) |
| **Certification DPF** | A verifier sur https://www.dataprivacyframework.gov/list |
| **Donnees autorisees** | Toutes categories : `PUBLIC`, `PERSONAL`, `CONFIDENTIAL`, `RESTRICTED` |
| **Clauses contractuelles** | Contrat de sous-traitance Art. 28 RGPD + DPA specifique |
| **Garanties specifiques** | Zero data retention pour les API (mode API sans retention), pas d'entrainement sur les donnees API |
| **Risques identifies** | Acces par les autorites americaines (FISA 702, EO 12333) -- attenue par le DPF |
| **Mesures supplementaires** | Chiffrement en transit (TLS 1.3), evaluation annuelle, option Azure en region UE |
| **Evaluation** | **Conforme** -- sous reserve de la validite du DPF et de la certification d'OpenAI. **Recommandation :** privilegier Azure OpenAI avec hebergement UE. |

#### 3.2.4 DeepSeek (Chine) -- TIER 2

| Aspect | Detail |
|--------|--------|
| **Siege** | Hangzhou, Zhejiang, Chine (RPC) |
| **Hebergement des donnees** | Chine (RPC) |
| **Mecanisme de transfert** | **Art. 46(2)(c) RGPD -- Clauses contractuelles types (CCT)** (Decision d'execution (UE) 2021/914) + mesures supplementaires |
| **Decision d'adequation** | **Aucune** -- La Commission europeenne n'a pas adopte de decision d'adequation pour la Chine |
| **Donnees autorisees** | **Tier 2 -- Donnees anonymisees uniquement** |
| **Donnees interdites** | Toute donnee a caractere personnel, toute donnee couverte par le secret professionnel |
| **Risques identifies** | Legislation chinoise sur la securite nationale (Loi sur la securite nationale 2015, Loi sur la cybersecurite 2017, Loi PIPL 2021) permettant un acces gouvernemental aux donnees ; absence de recours effectif pour les personnes concernees europeennes |
| **Mesures supplementaires** | (1) **Anonymisation prealable obligatoire** -- toutes les donnees sont anonymisees avant transmission ; (2) Chiffrement TLS 1.3 en transit ; (3) Clause contractuelle d'interdiction de retention et d'entrainement ; (4) Audit annuel |
| **Evaluation de l'efficacite des mesures** | L'anonymisation prealable elimine le risque de transfert de donnees personnelles. Les donnees transmises ne constituent plus des donnees a caractere personnel au sens de l'Art. 4(1) RGPD, rendant le Chapitre V inapplicable aux donnees effectivement transmises. |
| **Evaluation** | **Conforme** -- grace a l'anonymisation prealable qui exclut les donnees du champ d'application du RGPD. La conformite repose sur la qualite de l'anonymisation. |

#### 3.2.5 Zhipu AI GLM-4 (Chine) -- TIER 3

| Aspect | Detail |
|--------|--------|
| **Siege** | Pekin, Chine (RPC) |
| **Hebergement des donnees** | Chine (RPC) |
| **Mecanisme de transfert** | **Art. 46(2)(c) RGPD -- CCT** + mesures supplementaires |
| **Decision d'adequation** | **Aucune** |
| **Donnees autorisees** | **Tier 3 -- Donnees publiques uniquement** |
| **Donnees interdites** | Toute donnee a caractere personnel, toute donnee confidentielle, toute donnee anonymisee provenant de dossiers |
| **Donnees transmises** | Uniquement : textes legislatifs publics, jurisprudence publiee, questions juridiques generales sans lien avec un dossier |
| **Risques identifies** | Identiques a DeepSeek (legislation chinoise) -- mais risque attenue par la nature exclusivement publique des donnees |
| **Mesures supplementaires** | (1) **Filtrage strict** -- seules les donnees classees `PUBLIC` sont transmises ; (2) Verification automatique de l'absence de donnees personnelles ; (3) Chiffrement TLS 1.3 |
| **Evaluation** | **Conforme** -- les donnees publiques ne contiennent pas de donnees a caractere personnel. Le risque residuel est negligeable. |

#### 3.2.6 Moonshot AI Kimi (Chine) -- TIER 3

| Aspect | Detail |
|--------|--------|
| **Siege** | Pekin, Chine (RPC) |
| **Hebergement des donnees** | Chine (RPC) |
| **Mecanisme de transfert** | **Art. 46(2)(c) RGPD -- CCT** + mesures supplementaires |
| **Decision d'adequation** | **Aucune** |
| **Donnees autorisees** | **Tier 3 -- Donnees publiques uniquement** |
| **Donnees interdites** | Toute donnee a caractere personnel, toute donnee confidentielle, toute donnee anonymisee provenant de dossiers |
| **Donnees transmises** | Uniquement : textes legislatifs publics, jurisprudence publiee, questions juridiques generales sans lien avec un dossier |
| **Risques identifies** | Identiques a Zhipu AI |
| **Mesures supplementaires** | Identiques a Zhipu AI |
| **Evaluation** | **Conforme** -- identique a Zhipu AI. |

---

### 3.3 Tableau recapitulatif des transferts

```
+------------------+--------+----------------+------------------+---------------------+
| Fournisseur      | Pays   | Adequation     | Tier             | Donnees autorisees  |
+------------------+--------+----------------+------------------+---------------------+
| Mistral AI       | FR/UE  | UE (pas de     | Tier 1           | Toutes              |
|                  |        | transfert)     |                  |                     |
+------------------+--------+----------------+------------------+---------------------+
| Anthropic Claude | US     | EU-US DPF      | Tier 1           | Toutes              |
+------------------+--------+----------------+------------------+---------------------+
| OpenAI GPT-4     | US     | EU-US DPF      | Tier 1           | Toutes              |
+------------------+--------+----------------+------------------+---------------------+
| DeepSeek         | CN     | NON            | Tier 2           | Anonymisees         |
|                  |        |                |                  | uniquement          |
+------------------+--------+----------------+------------------+---------------------+
| Zhipu AI GLM-4   | CN     | NON            | Tier 3           | Publiques           |
|                  |        |                |                  | uniquement          |
+------------------+--------+----------------+------------------+---------------------+
| Moonshot Kimi    | CN     | NON            | Tier 3           | Publiques           |
|                  |        |                |                  | uniquement          |
+------------------+--------+----------------+------------------+---------------------+
```

---

### 3.4 Obligations supplementaires

1. **Revue annuelle** de la decision d'adequation EU-US DPF (risque d'invalidation, cf. precedents Schrems I et Schrems II).
2. **Monitoring** des developpements legislatifs en Chine (PIPL, Loi sur la cybersecurite, Loi sur la securite des donnees).
3. **Clause de suspension automatique** : en cas d'invalidation du DPF ou de changement legislatif significatif, les transferts vers les fournisseurs concernes sont suspendus automatiquement.
4. **Evaluation TIA (Transfer Impact Assessment)** documentee pour chaque fournisseur hors UE, revue annuellement.

---

## 4. AI ACT UE -- CHECKLIST DE CONFORMITE (Reglement 2024/1689)

### 4.1 Classification du systeme

Le module LLM Gateway de LexiBel constitue un **systeme d'IA a haut risque** au sens de l'AI Act UE :

- **Art. 6(2) :** Le systeme est vise a l'Annexe III.
- **Annexe III, point 8 :** "Administration de la justice et processus democratiques" -- systemes d'IA destines a etre utilises pour aider une autorite judiciaire dans la recherche et l'interpretation des faits et du droit et dans l'application du droit a un ensemble concret de faits.
- **Application par analogie :** Bien que les avocats ne soient pas des autorites judiciaires, l'utilisation d'IA pour l'analyse juridique et la redaction de documents juridiques releve de l'ecosysteme de la justice et comporte des risques comparables pour les droits fondamentaux des personnes.

> **Note :** Si la classification en haut risque etait contestee, le systeme resterait soumis aux obligations de transparence de l'Art. 50 (systemes d'IA a usage general interagissant avec des personnes physiques).

---

### 4.2 Checklist de conformite -- Systeme d'IA a haut risque

#### 4.2.1 Systeme de gestion des risques (Art. 9)

- [x] **Art. 9(1) :** Un systeme de gestion des risques est etabli, mis en oeuvre, documente et tenu a jour.
- [x] **Art. 9(2)(a) :** Les risques connus et raisonnablement previsibles sont identifies et analyses.
- [x] **Art. 9(2)(b) :** Les risques sont estimes et evalues (cf. Section 2.4 du present document).
- [x] **Art. 9(2)(c) :** Les risques sont evalues apres mise sur le marche et en conditions reelles.
- [x] **Art. 9(2)(d) :** Des mesures de gestion des risques appropriees sont adoptees (cf. Section 2.5).
- [x] **Art. 9(3) :** Les risques residuels sont juges acceptables.
- [x] **Art. 9(4) :** Les mesures tiennent compte des effets et interactions possibles.
- [ ] **Art. 9(5) :** Les tests sont effectues a des moments appropries du developpement. *(En cours -- a documenter lors du deploiement)*
- [x] **Art. 9(6) :** Le systeme de gestion des risques est concu pour etre iteratif et mis a jour regulierement.

#### 4.2.2 Donnees et gouvernance des donnees (Art. 10)

- [x] **Art. 10(1) :** Les jeux de donnees d'entrainement, de validation et de test sont soumis a des pratiques de gouvernance appropriees.
- [x] **Art. 10(2) :** Les jeux de donnees font l'objet de choix de conception, de collecte et de preparation des donnees documentes.
  - *Note : LexiBel n'entraine pas ses propres modeles mais utilise des API. La gouvernance porte sur les donnees transmises aux API.*
- [x] **Art. 10(3) :** Les jeux de donnees sont pertinents, suffisamment representatifs et, dans la mesure du possible, exempts d'erreurs et complets.
- [x] **Art. 10(4) :** Les jeux de donnees tiennent compte des caracteristiques propres aux personnes ou groupes de personnes specifiques.
- [x] **Art. 10(5) :** Le traitement de categories particulieres de donnees est strictement necessaire et encadre.

#### 4.2.3 Documentation technique (Art. 11)

- [x] **Art. 11(1) :** La documentation technique est redigee avant la mise sur le marche et tenue a jour.
- [x] **Art. 11(1), Annexe IV :** La documentation contient les informations visees a l'Annexe IV :
  - [x] Description generale du systeme d'IA
  - [x] Description des elements du systeme et de son processus de developpement
  - [x] Informations sur le fonctionnement du systeme
  - [x] Description du systeme de gestion des risques
  - [x] Description des modifications apportees au systeme au cours de son cycle de vie
  - [ ] Liste des normes harmonisees appliquees *(a completer -- normes en cours d'adoption)*
  - [x] Description des mesures de cybersecurite

#### 4.2.4 Tenue de registres -- Journalisation (Art. 12)

- [x] **Art. 12(1) :** Le systeme permet l'enregistrement automatique des evenements (logs).
- [x] **Art. 12(2) :** Les logs permettent la tracabilite du fonctionnement tout au long du cycle de vie.
- [x] **Art. 12(3) :** Les logs incluent :
  - [x] La periode d'utilisation (date/heure de debut et fin)
  - [x] La base de donnees de reference (fournisseur LLM utilise)
  - [x] Les donnees d'entree (hash du prompt, classification)
  - [x] L'identification des personnes physiques impliquees dans la verification des resultats (avocat utilisateur)
- [x] **Art. 12(4) :** Les logs sont conserves pendant une duree appropriee (5 ans).

#### 4.2.5 Transparence et information des utilisateurs (Art. 13)

- [x] **Art. 13(1) :** Le systeme est concu pour etre suffisamment transparent pour permettre aux utilisateurs d'interpreter les resultats.
- [x] **Art. 13(2) :** Le systeme est accompagne d'une notice d'utilisation comprenant :
  - [x] L'identite et les coordonnees du fournisseur (Clixite SRL)
  - [x] Les caracteristiques, capacites et limites du systeme
  - [x] Les modifications predeterminees
  - [x] Les mesures de controle humain
  - [x] La duree de vie attendue du systeme et les mesures de maintenance
  - [x] Les specifications d'entree (types de prompts acceptes)

#### 4.2.6 Controle humain (Art. 14)

- [x] **Art. 14(1) :** Le systeme est concu pour etre effectivement controle par des personnes physiques (avocats).
- [x] **Art. 14(2) :** Le controle humain vise a prevenir ou reduire au minimum les risques.
- [x] **Art. 14(3) :** Les mesures de controle humain comprennent :
  - [x] **(a)** L'identification et la comprehension des capacites et limites du systeme
  - [x] **(b)** La conscience d'un possible biais d'automatisation (automation bias)
  - [x] **(c)** L'interpretation correcte des resultats du systeme
  - [x] **(d)** La possibilite de ne pas utiliser le systeme ou d'ignorer ses resultats
  - [x] **(e)** La possibilite d'interrompre le fonctionnement du systeme (bouton d'arret)
- [x] **Art. 14(4) :** L'avocat conserve la **decision finale** sur l'utilisation des resultats du LLM. Le systeme ne prend aucune decision autonome.

#### 4.2.7 Exactitude, robustesse et cybersecurite (Art. 15)

- [x] **Art. 15(1) :** Le systeme est concu pour atteindre un niveau d'exactitude, de robustesse et de cybersecurite approprie.
- [x] **Art. 15(2) :** Les niveaux d'exactitude sont declares et communiques aux utilisateurs.
  - *Avertissement systematique : "Les reponses du LLM peuvent contenir des erreurs. La verification humaine est obligatoire."*
- [x] **Art. 15(3) :** Le systeme est resilient aux erreurs, defaillances et incoherences.
  - *Mecanisme de fallback : si un fournisseur est indisponible, rerouting vers un fournisseur alternatif du meme tier.*
- [x] **Art. 15(4) :** Le systeme est protege contre les tentatives de manipulation par des tiers.
  - *Protection contre les prompt injections, validation des entrees, sandboxing des reponses.*
- [x] **Art. 15(5) :** Le systeme dispose de mecanismes de cybersecurite :
  - [x] Chiffrement TLS 1.3
  - [x] Authentification multi-facteurs
  - [x] Controle d'acces RBAC
  - [x] Journalisation des acces
  - [x] Protection contre les fuites de donnees (DLP)

#### 4.2.8 Obligations du deployeur (Art. 26)

Le cabinet d'avocats, en tant que **deployeur** du systeme d'IA a haut risque, doit :

- [x] **Art. 26(1) :** Prendre des mesures techniques et organisationnelles pour garantir l'utilisation conformement a la notice.
- [x] **Art. 26(2) :** Confier le controle humain a des personnes competentes (avocats formes).
- [ ] **Art. 26(3) :** S'assurer que les donnees d'entree sont pertinentes et representatives. *(Responsabilite de l'avocat utilisateur)*
- [x] **Art. 26(4) :** Surveiller le fonctionnement du systeme sur la base de la notice.
- [x] **Art. 26(5) :** Conserver les logs generes automatiquement pendant la duree prevue (5 ans).
- [x] **Art. 26(6) :** Realiser l'analyse d'impact sur les droits fondamentaux (cf. DPIA Section 2).
- [x] **Art. 26(7) :** Cooperer avec les autorites de surveillance du marche.
- [x] **Art. 26(8) :** Informer les personnes physiques concernees qu'elles sont soumises a un systeme d'IA a haut risque.

#### 4.2.9 Obligations de transparence (Art. 50)

- [x] **Art. 50(1) :** Les personnes physiques sont informees qu'elles interagissent avec un systeme d'IA (le cas echeant).
- [x] **Art. 50(2) :** Les contenus generes par IA sont marques comme tels.
  - *Chaque document genere ou assiste par le LLM porte la mention : "Document assiste par intelligence artificielle -- a verifier par un avocat."*
- [x] **Art. 50(4) :** Les contenus generes par IA sont detectables par des moyens techniques.
  - *Metadonnees du document incluant l'identifiant du modele LLM utilise, la date et l'heure de generation.*

#### 4.2.10 Enregistrement dans la base de donnees de l'UE (Art. 49 et Art. 71)

- [ ] **Art. 49(1) :** Le fournisseur enregistre le systeme dans la base de donnees de l'UE avant sa mise sur le marche. *(A completer par Clixite SRL avant deploiement)*
- [ ] **Art. 49(3) :** Le deployeur enregistre son utilisation du systeme. *(A completer par chaque cabinet)*

> **Calendrier AI Act :** Les obligations relatives aux systemes a haut risque de l'Annexe III entrent en application le **2 aout 2026** (Art. 113(3)(b)). La mise en conformite doit etre achevee avant cette date.

---

## 5. SECRET PROFESSIONNEL BELGE

### 5.1 Cadre legal

Le secret professionnel de l'avocat en Belgique repose sur un triple fondement :

#### 5.1.1 Article 458 du Code penal

> *"Les medecins, chirurgiens, officiers de sante, pharmaciens, sages-femmes et toutes autres personnes depositaires, par etat ou par profession, des secrets qu'on leur confie, qui, hors le cas ou ils sont appeles a rendre temoignage en justice ou devant une commission d'enquete parlementaire et celui ou la loi, le decret ou l'ordonnance les oblige ou les autorise a faire connaitre ces secrets, les auront reveles, seront punis d'un emprisonnement d'un an a trois ans et d'une amende de cent euros a mille euros ou d'une de ces peines seulement."*

**Implications pour le LLM Gateway :**

- La transmission de donnees couvertes par le secret professionnel a un tiers (fournisseur LLM) constitue potentiellement une **violation de l'article 458 C.P.**, passible de sanctions penales.
- L'avocat reste **personnellement responsable** du respect du secret professionnel, y compris lorsqu'il utilise des outils technologiques.
- La violation du secret professionnel est un **delit penal**, independant de toute plainte de la personne concernee (poursuite d'office possible).

**Mesures d'attenuation dans LexiBel :**

1. **Consentement eclaire du client :** Le client consent expressement a l'utilisation d'outils d'IA pour le traitement de son dossier, apres avoir ete informe des risques.
2. **Classification et routing :** Les donnees les plus sensibles ne sont envoyees qu'aux fournisseurs Tier 1 (UE ou DPF).
3. **Anonymisation :** Pour les fournisseurs Tier 2, toutes les donnees identifiantes sont supprimees avant envoi, de sorte que les donnees transmises ne sont plus couvertes par le secret professionnel (elles ne permettent plus d'identifier la personne concernee).
4. **Donnees publiques uniquement pour Tier 3 :** Les fournisseurs chinois sans adequation ne recoivent que des donnees deja publiques (legislation, jurisprudence publiee), qui ne sont pas couvertes par le secret professionnel.
5. **Interdiction contractuelle d'entrainement :** Les fournisseurs s'engagent a ne pas utiliser les donnees pour entrainer leurs modeles.

#### 5.1.2 Position doctrinale et jurisprudentielle

La Cour de cassation belge a rappele a plusieurs reprises le caractere **absolu** du secret professionnel de l'avocat (Cass., 19 novembre 2003, Pas., 2003, p. 1841). Ce caractere absolu signifie que :

- Le secret couvre **tout** ce que l'avocat apprend dans l'exercice de sa profession.
- Le secret est **d'ordre public** -- il ne peut y etre renonce, meme avec le consentement du client (position majoritaire, mais nuancee par une partie de la doctrine).
- Le secret s'etend aux **collaborateurs** de l'avocat et aux **prestataires techniques** qui accedent aux informations.

> **Debat doctrinal sur le consentement du client :** Une partie de la doctrine considere que le consentement du client ne suffit pas a lever le secret professionnel (caractere d'ordre public). Toutefois, dans le contexte des outils technologiques necessaires a l'exercice de la profession, la doctrine majoritaire et les barreaux admettent que l'avocat peut faire appel a des prestataires techniques sous reserve de garanties contractuelles et techniques adequates (cf. Recommandations Avocats.be sur le cloud computing).

---

### 5.2 Reglement Obas (Orde van Vlaamse Balies)

#### 5.2.1 Dispositions pertinentes

Le Reglement de l'Orde van Vlaamse Balies contient plusieurs dispositions applicables a l'utilisation d'outils d'IA :

| Article | Objet | Application au LLM Gateway |
|---------|-------|--------------------------|
| **Art. 4 -- Secret professionnel** | L'avocat est tenu au secret professionnel conformement a l'article 458 C.P. | Obligation de proteger les donnees des clients lors de l'utilisation du LLM |
| **Art. 138 -- Moyens techniques** | L'avocat utilise des moyens techniques offrant des garanties suffisantes de confidentialite | Le LLM Gateway doit offrir des garanties techniques (chiffrement, anonymisation) |
| **Art. 139 -- Sous-traitants** | L'avocat s'assure que ses sous-traitants respectent le secret professionnel | Contrats avec Clixite SRL et les fournisseurs LLM incluant des clauses de confidentialite |

#### 5.2.2 Obligations specifiques

1. **Information au batonnier :** L'utilisation d'un systeme d'IA pour le traitement des dossiers doit etre signalee au batonnier si celui-ci le demande.
2. **Controle deontologique :** Le batonnier peut a tout moment verifier que les mesures de protection du secret professionnel sont adequates.
3. **Responsabilite disciplinaire :** L'avocat qui manque a ses obligations de confidentialite s'expose a des sanctions disciplinaires, independamment des sanctions penales.

---

### 5.3 Recommandations Avocats.be (Ordre des barreaux francophones et germanophone)

#### 5.3.1 Recommandations sur le cloud computing

Avocats.be a emis des recommandations sur l'utilisation du cloud computing par les avocats, qui s'appliquent par analogie aux services d'IA :

| Recommandation | Application au LLM Gateway |
|---------------|--------------------------|
| **Localisation des donnees dans l'UE** | Privilegier les fournisseurs Tier 1 (Mistral dans l'UE, Anthropic et OpenAI via DPF) |
| **Chiffrement des donnees** | TLS 1.3 en transit, AES-256 au repos |
| **Contrat de sous-traitance** | Contrats Art. 28 RGPD avec tous les fournisseurs |
| **Audit des prestataires** | Audit annuel des fournisseurs LLM |
| **Droit de retrait des donnees** | Clause de suppression des donnees en cas de fin de contrat |
| **Pas de transfert hors UE sans garanties** | Systeme de tiers avec anonymisation/donnees publiques pour les fournisseurs hors UE sans adequation |

#### 5.3.2 Recommandations specifiques a l'IA

> **Note :** Les recommandations specifiques d'Avocats.be sur l'utilisation de l'IA par les avocats sont en cours d'elaboration. Les principes suivants sont appliques par anticipation :

1. **L'avocat reste maitre de son travail :** Le LLM est un outil d'assistance, pas un substitut a l'analyse juridique de l'avocat.
2. **Verification obligatoire :** Toute production du LLM doit etre verifiee par l'avocat avant utilisation.
3. **Transparence envers le client :** Le client doit etre informe de l'utilisation d'outils d'IA dans le traitement de son dossier.
4. **Interdiction de delegation de la decision :** L'avocat ne peut deleguer sa prise de decision a un systeme d'IA.
5. **Formation continue :** Les avocats utilisant des outils d'IA doivent se former a leur fonctionnement et a leurs limites.

---

### 5.4 Matrice de conformite secret professionnel x tiers

| Type de donnees | Secret prof. | Tier 1 (UE/DPF) | Tier 2 (Anonymise) | Tier 3 (Public) |
|----------------|-------------|-----------------|-------------------|----------------|
| Document de dossier (confidentiel) | **Couvert** | AUTORISE (avec consentement client) | AUTORISE (apres anonymisation -- plus couvert) | **INTERDIT** |
| Correspondance avocat-client | **Couvert** | AUTORISE (avec consentement client) | AUTORISE (apres anonymisation -- plus couvert) | **INTERDIT** |
| Notes internes | **Couvert** | AUTORISE (avec consentement client) | AUTORISE (apres anonymisation -- plus couvert) | **INTERDIT** |
| Donnees d'identification du client | **Couvert** | AUTORISE (avec consentement client) | **INTERDIT** (doit etre anonymise) | **INTERDIT** |
| Legislation publiee | Non couvert | AUTORISE | AUTORISE | AUTORISE |
| Jurisprudence publiee | Non couvert | AUTORISE | AUTORISE | AUTORISE |
| Doctrine publiee | Non couvert | AUTORISE | AUTORISE | AUTORISE |
| Question juridique generale | Non couvert | AUTORISE | AUTORISE | AUTORISE |

---

### 5.5 Procedure de verification pre-envoi

Avant chaque envoi de donnees a un fournisseur LLM, le systeme LexiBel execute la procedure suivante :

```
1. CLASSIFICATION AUTOMATIQUE du contenu du prompt
   |
   +--> Classification = PUBLIC ?
   |    OUI --> Tous les tiers autorises (Tier 1, 2, 3)
   |    NON --> Etape 2
   |
   +--> Classification = PERSONAL ?
   |    OUI --> Tier 1 uniquement OU Tier 2 apres anonymisation
   |    NON --> Etape 3
   |
   +--> Classification = CONFIDENTIAL ?
   |    OUI --> Tier 1 uniquement (avec consentement client verifie)
   |    NON --> Etape 4
   |
   +--> Classification = RESTRICTED ?
        OUI --> Tier 1 uniquement (avec consentement client explicite
                + validation de l'avocat)

2. VERIFICATION DU CONSENTEMENT CLIENT
   +--> Consentement enregistre pour ce type de traitement ?
        OUI --> Continuer
        NON --> BLOQUER et demander le consentement

3. ANONYMISATION (si Tier 2)
   +--> Execution du moteur NER + regex
   +--> Verification du score d'anonymisation
   +--> Score >= seuil ? OUI --> Continuer / NON --> BLOQUER

4. ENVOI au fournisseur LLM selectionne

5. JOURNALISATION de la transaction (log d'audit)
```

---

## 6. ANNEXES

### Annexe A -- Glossaire

| Terme | Definition |
|-------|-----------|
| **APD/GBA** | Autorite de protection des donnees (Belgique) / Gegevensbeschermingsautoriteit |
| **CCT** | Clauses contractuelles types (Standard Contractual Clauses) |
| **DPF** | Data Privacy Framework (EU-US) |
| **DPO** | Delegue a la protection des donnees (Data Protection Officer) |
| **DPIA** | Analyse d'impact relative a la protection des donnees (Data Protection Impact Assessment) |
| **LLM** | Large Language Model (modele de langage de grande taille) |
| **NER** | Named Entity Recognition (reconnaissance d'entites nommees) |
| **NISS** | Numero d'identification a la securite sociale (numero de registre national belge) |
| **PIPL** | Personal Information Protection Law (loi chinoise sur la protection des informations personnelles) |
| **RBAC** | Role-Based Access Control (controle d'acces base sur les roles) |
| **RGPD** | Reglement general sur la protection des donnees (Regulation (EU) 2016/679) |
| **TIA** | Transfer Impact Assessment (evaluation de l'impact des transferts) |
| **Tier** | Niveau de classification determinant les fournisseurs LLM autorises |

### Annexe B -- References legales

| Reference | Titre |
|-----------|-------|
| Reglement (UE) 2016/679 | Reglement general sur la protection des donnees (RGPD) |
| Reglement (UE) 2024/1689 | Reglement sur l'intelligence artificielle (AI Act) |
| Decision d'execution (UE) 2023/1795 | Decision d'adequation EU-US Data Privacy Framework |
| Decision d'execution (UE) 2021/914 | Clauses contractuelles types pour les transferts internationaux |
| Loi du 30 juillet 2018 | Protection des personnes physiques a l'egard des traitements de donnees (Belgique) |
| Article 458 Code penal belge | Secret professionnel |
| Reglement Obas | Reglement de l'Orde van Vlaamse Balies |
| PIPL (2021) | Personal Information Protection Law (Chine) |

### Annexe C -- Historique des versions

| Version | Date | Auteur | Modifications |
|---------|------|--------|---------------|
| 1.0 | 2026-02-18 | Clixite SRL | Version initiale |

### Annexe D -- Validation

| Role | Nom | Date | Signature |
|------|-----|------|-----------|
| Redacteur technique | Clixite SRL | 2026-02-18 | _________________ |
| DPO du cabinet | [A completer] | [A completer] | _________________ |
| Avocat responsable | [A completer] | [A completer] | _________________ |
| Batonnier (si requis) | [A completer] | [A completer] | _________________ |

---

**FIN DU DOCUMENT**

*Ce document est confidentiel et destine exclusivement aux responsables du traitement (cabinets d'avocats) et au sous-traitant (Clixite SRL). Toute diffusion non autorisee est interdite.*
