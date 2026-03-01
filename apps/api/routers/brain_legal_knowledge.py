"""Belgian legal knowledge base — jurisdiction, deadlines, documents, references.

Used by the dossier/contact creation assistants to provide intelligent
recommendations based on Belgian law.
"""

BELGIAN_LEGAL_KNOWLEDGE: dict[str, dict] = {
    "civil": {
        "jurisdiction": "Tribunal de premiere instance (section civile)",
        "sub_types": [
            "responsabilite contractuelle",
            "responsabilite extracontractuelle",
            "recouvrement de creance",
            "servitudes",
            "troubles de voisinage",
            "bail",
        ],
        "deadlines": [
            {
                "name": "Prescription de droit commun",
                "duration": "10 ans",
                "description": "Art. 2262bis C. civ. — prescription de droit commun pour les actions personnelles",
            },
            {
                "name": "Prescription responsabilite extracontractuelle",
                "duration": "5 ans",
                "description": "Art. 2262bis §1 al.2 C. civ. — a partir de la connaissance du dommage",
            },
            {
                "name": "Delai d'appel",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud. — a compter de la signification du jugement",
            },
            {
                "name": "Pourvoi en cassation",
                "duration": "3 mois",
                "description": "Art. 1073 C. jud. — a compter de la signification de la decision",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Pieces d'identite du client",
            "Contrat ou convention litigieuse",
            "Correspondances echangees entre les parties",
            "Preuves du dommage (factures, photos, expertises)",
            "Mise en demeure prealable",
        ],
        "risk_points": [
            "Verifier la prescription avant toute action",
            "Evaluer la solvabilite de la partie adverse",
            "Verifier la competence territoriale du tribunal",
            "Analyser les clauses attributives de competence",
            "Examiner les clauses de mediation ou arbitrage prealable",
        ],
        "legal_references": [
            "Code civil (art. 1101 et s. — obligations)",
            "Code judiciaire (art. 1050-1073 — voies de recours)",
            "Code judiciaire (art. 624-633 — competence territoriale)",
            "Loi du 21 février 2005 sur la mediation",
        ],
        "strategy_notes": "En matiere civile belge, privilegier la mise en demeure detaillee avant toute citation. "
        "Evaluer l'opportunite d'une mediation (obligatoire en certaines matieres depuis 2024). "
        "Verifier les conditions de l'aide juridique si le client y a droit.",
    },
    "penal": {
        "jurisdiction": "Tribunal correctionnel / Cour d'assises",
        "sub_types": [
            "plainte avec constitution de partie civile",
            "defense en correctionnelle",
            "instruction penale",
            "detention preventive",
            "execution des peines",
            "mediation penale",
        ],
        "deadlines": [
            {
                "name": "Prescription contraventions",
                "duration": "6 mois",
                "description": "Art. 68 C. pen. — prescription de l'action publique pour les contraventions",
            },
            {
                "name": "Prescription delits",
                "duration": "5 ans",
                "description": "Art. 68 C. pen. — prescription de l'action publique pour les delits",
            },
            {
                "name": "Prescription crimes",
                "duration": "15 ans",
                "description": "Art. 68 C. pen. — prescription de l'action publique pour les crimes",
            },
            {
                "name": "Delai d'appel (penal)",
                "duration": "30 jours",
                "description": "Art. 203 C.I.Cr. — a compter du prononce du jugement",
            },
            {
                "name": "Chambre du conseil (detention preventive)",
                "duration": "5 jours",
                "description": "Art. 21 Loi du 20/07/1990 — comparution dans les 5 jours du mandat d'arret",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Proces-verbal de police / plainte",
            "Copie du dossier repressif (acces au dossier)",
            "Pieces d'identite du client",
            "Casier judiciaire du client",
            "Elements a decharge",
        ],
        "risk_points": [
            "Verifier le respect des droits de la defense (acces au dossier, Salduz)",
            "Controler la regularite des devoirs d'enquete",
            "Evaluer le risque de detention preventive",
            "Verifier la qualification penale retenue",
            "Examiner les possibilites de transaction penale (art. 216bis C.I.Cr.)",
        ],
        "legal_references": [
            "Code penal (Livre I et II)",
            "Code d'instruction criminelle (art. 182 et s.)",
            "Loi du 20 juillet 1990 relative a la detention preventive",
            "Loi Salduz du 13 aout 2011 (assistance de l'avocat)",
            "Loi du 5 mai 2014 relative a l'internement",
        ],
        "strategy_notes": "En matiere penale, l'acces au dossier est fondamental (art. 21bis C.I.Cr.). "
        "Verifier immediatement les delais de detention preventive et les conditions de remise en liberte. "
        "Envisager la mediation penale ou la transaction si les faits s'y pretent.",
    },
    "commercial": {
        "jurisdiction": "Tribunal de l'entreprise",
        "sub_types": [
            "litiges entre entreprises",
            "droit des contrats commerciaux",
            "concurrence deloyale",
            "recouvrement commercial",
            "faillite et reorganisation judiciaire",
            "droit des marques",
        ],
        "deadlines": [
            {
                "name": "Prescription commerciale",
                "duration": "10 ans",
                "description": "Art. 2262bis C. civ. — prescription de droit commun applicable aux obligations commerciales",
            },
            {
                "name": "Delai de paiement (B2B)",
                "duration": "30 jours",
                "description": "Loi du 2 aout 2002 — delai de paiement par defaut entre entreprises",
            },
            {
                "name": "Declaration de cessation de paiement",
                "duration": "1 mois",
                "description": "Art. XX.102 CDE — obligation de declaration dans le mois de la cessation",
            },
            {
                "name": "Delai d'appel",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud. — a compter de la signification du jugement",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Extrait BCE/KBO de l'entreprise cliente",
            "Contrat commercial litigieux",
            "Factures et bons de commande",
            "Correspondances commerciales",
            "Comptes annuels des parties (via BNB)",
        ],
        "risk_points": [
            "Verifier la qualite de commercant/entreprise des parties",
            "Analyser les conditions generales applicables",
            "Evaluer le risque d'insolvabilite (via Banque-Carrefour des Entreprises)",
            "Verifier l'existence de clauses compromissoires",
            "Examiner les pratiques du marche pertinent",
        ],
        "legal_references": [
            "Code de droit economique (CDE, Livres I-XX)",
            "Code judiciaire (art. 573-574 — competence du tribunal de l'entreprise)",
            "Loi du 2 aout 2002 concernant la lutte contre le retard de paiement",
            "Livre XX CDE — insolvabilite des entreprises",
        ],
        "strategy_notes": "En matiere commerciale belge, la procedure sommaire inedite (PSI) permet une resolution rapide. "
        "Verifier si une reorganisation judiciaire (Livre XX CDE) est envisageable pour l'adversaire. "
        "Les conditions generales de vente doivent etre analysees avec soin (battle of the forms).",
    },
    "social": {
        "jurisdiction": "Tribunal du travail",
        "sub_types": [
            "licenciement abusif",
            "contrat de travail",
            "securite sociale",
            "accidents du travail",
            "discrimination au travail",
            "harcelement",
        ],
        "deadlines": [
            {
                "name": "Prescription actions contractuelles (travail)",
                "duration": "1 an",
                "description": "Art. 15 Loi du 3/07/1978 — prescription des actions naissant du contrat de travail",
            },
            {
                "name": "Contestation du licenciement",
                "duration": "1 an",
                "description": "CCT n°109 — delai pour contester le caractere manifestement deraisonnable du licenciement",
            },
            {
                "name": "Delai de preavis",
                "duration": "Variable selon anciennete",
                "description": "Art. 37/2 Loi du 3/07/1978 — selon l'anciennete du travailleur (statut unique)",
            },
            {
                "name": "Delai d'appel",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud. — a compter de la signification du jugement",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Contrat de travail",
            "Fiches de paie recentes",
            "Lettre de licenciement / preavis",
            "Reglement de travail",
            "Correspondances avec l'employeur",
            "Certificat medical (si applicable)",
        ],
        "risk_points": [
            "Verifier le respect de la procedure de licenciement (motivation — CCT 109)",
            "Controler le calcul de l'indemnite de preavis (statut unique)",
            "Examiner les protections speciales (grossesse, mandat syndical, etc.)",
            "Evaluer les indemnites reclamables (preavis, dommages, protection)",
            "Verifier l'application de la clause de non-concurrence",
        ],
        "legal_references": [
            "Loi du 3 juillet 1978 relative aux contrats de travail",
            "CCT n°109 du CNT — licenciement manifestement deraisonnable",
            "Loi du 10 mai 2007 — anti-discrimination",
            "Loi du 4 aout 1996 — bien-etre au travail",
            "Code judiciaire (art. 578-583 — competence du tribunal du travail)",
        ],
        "strategy_notes": "En droit social belge, le tribunal du travail a une competence exclusive. "
        "La charge de la preuve en matiere de licenciement pese sur l'employeur (motivation — CCT 109). "
        "Envisager la conciliation obligatoire devant le bureau de conciliation du tribunal du travail.",
    },
    "fiscal": {
        "jurisdiction": "Tribunal de premiere instance (section fiscale)",
        "sub_types": [
            "impot des personnes physiques (IPP)",
            "impot des societes (ISoc)",
            "TVA",
            "droits de succession",
            "droits d'enregistrement",
            "procedure fiscale",
        ],
        "deadlines": [
            {
                "name": "Reclamation administrative",
                "duration": "6 mois",
                "description": "Art. 371 CIR 92 — a compter de l'envoi de l'avertissement-extrait de role",
            },
            {
                "name": "Recours judiciaire",
                "duration": "3 mois",
                "description": "Art. 1385undecies C. jud. — a compter de la notification de la decision directoriale",
            },
            {
                "name": "Prescription fiscale ordinaire",
                "duration": "3 ans",
                "description": "Art. 354 CIR 92 — prescription de l'imposition supplementaire",
            },
            {
                "name": "Prescription fiscale extraordinaire",
                "duration": "7 ans",
                "description": "Art. 354 al.2 CIR 92 — en cas de fraude fiscale",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Avertissement-extrait de role conteste",
            "Declaration fiscale concernee",
            "Notification de rectification (le cas echeant)",
            "Correspondances avec l'administration fiscale",
            "Pieces comptables justificatives",
        ],
        "risk_points": [
            "Verifier le respect des delais de reclamation (forclusion)",
            "Analyser la validite de la procedure de taxation",
            "Evaluer le risque de sanctions administratives et penales",
            "Verifier l'existence d'un ruling fiscal prealable",
            "Examiner les conventions preventives de double imposition",
        ],
        "legal_references": [
            "Code des impots sur les revenus 1992 (CIR 92)",
            "Code de la TVA",
            "Code des droits de succession",
            "Code des droits d'enregistrement",
            "Code judiciaire (art. 569 al.1, 32° — competence fiscale)",
            "Charte du contribuable (Loi du 4 aout 1986)",
        ],
        "strategy_notes": "En matiere fiscale belge, la reclamation administrative est un prealable obligatoire avant le recours judiciaire. "
        "Le delai de 6 mois pour reclamer est imperatif et de rigueur. "
        "Envisager un accord avec l'administration via la mediation fiscale (Service de conciliation fiscale).",
    },
    "family": {
        "jurisdiction": "Tribunal de la famille",
        "sub_types": [
            "divorce par consentement mutuel",
            "divorce pour desunion irreparable",
            "autorite parentale",
            "obligations alimentaires",
            "filiation",
            "adoption",
            "regime matrimonial",
        ],
        "deadlines": [
            {
                "name": "Delai de reflexion (divorce consentement mutuel)",
                "duration": "3 mois (si enfant mineur) / pas de delai sinon",
                "description": "Art. 1289 C. jud. — delai de comparution supprime ou reduit",
            },
            {
                "name": "Delai d'appel (famille)",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud. — a compter de la signification du jugement",
            },
            {
                "name": "Action en contestation de paternite",
                "duration": "1 an",
                "description": "Art. 318 C. civ. — a compter de la decouverte du fait",
            },
            {
                "name": "Prescription aliments",
                "duration": "5 ans",
                "description": "Art. 2277 C. civ. — arrieres de pensions alimentaires",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Acte de mariage",
            "Actes de naissance des enfants",
            "Composition de menage",
            "Preuves de revenus des parties (fiches de paie, avertissements-extraits de role)",
            "Inventaire du patrimoine commun",
            "Convention prealable (si divorce amiable)",
        ],
        "risk_points": [
            "Proteger les interets des enfants mineurs en priorite",
            "Evaluer les mesures urgentes et provisoires necessaires",
            "Verifier l'inventaire complet du patrimoine commun",
            "Analyser le regime matrimonial applicable",
            "Examiner les droits de la partie la plus faible economiquement",
        ],
        "legal_references": [
            "Code civil (art. 229 et s. — divorce)",
            "Code civil (art. 371-387 — autorite parentale)",
            "Code judiciaire (art. 1253ter et s. — tribunal de la famille)",
            "Loi du 19 mars 2010 — tribunal de la famille et de la jeunesse",
            "Code civil (art. 203-211 — obligations alimentaires)",
        ],
        "strategy_notes": "Le tribunal de la famille est competent pour l'ensemble du contentieux familial depuis 2014. "
        "Privilegier le divorce par consentement mutuel quand c'est possible (plus rapide et moins couteux). "
        "En cas de violence conjugale, envisager immediatement une ordonnance d'eloignement.",
    },
    "administrative": {
        "jurisdiction": "Conseil d'Etat (section du contentieux administratif)",
        "sub_types": [
            "recours en annulation",
            "recours en suspension",
            "marches publics",
            "urbanisme et environnement",
            "fonction publique",
            "etrangers et asile",
        ],
        "deadlines": [
            {
                "name": "Recours en annulation",
                "duration": "60 jours",
                "description": "Art. 4 Arrete du Regent du 23/08/1948 — a compter de la notification ou publication",
            },
            {
                "name": "Demande de suspension (extreme urgence)",
                "duration": "15 jours",
                "description": "Art. 17 §1 Lois coordonnees — suspension d'extreme urgence",
            },
            {
                "name": "Recours marches publics",
                "duration": "15 jours (suspension) / 60 jours (annulation)",
                "description": "Loi du 17/06/2013 — delais specifiques en matiere de marches publics",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Acte administratif attaque (decision, permis, arrete)",
            "Preuve de notification de la decision",
            "Dossier administratif complet",
            "Memoire en requete (formalisme strict)",
            "Pieces justificatives du prejudice",
        ],
        "risk_points": [
            "Respecter strictement le delai de 60 jours (delai de forclusion)",
            "Verifier l'epuisement des recours administratifs internes",
            "Evaluer l'interet au recours (interet personnel, direct et actuel)",
            "Identifier les moyens d'annulation (incompetence, vice de forme, violation de la loi, detournement de pouvoir)",
            "Envisager la demande de suspension si urgence",
        ],
        "legal_references": [
            "Lois coordonnees sur le Conseil d'Etat du 12 janvier 1973",
            "Arrete du Regent du 23 aout 1948 — procedure devant le Conseil d'Etat",
            "Loi du 17 juin 2013 — marches publics",
            "CoBAT / CoDT — urbanisme (selon la region)",
        ],
        "strategy_notes": "La procedure devant le Conseil d'Etat est ecrite et formaliste. "
        "L'auditeur joue un role determinant — analyser soigneusement son rapport. "
        "En matiere d'urbanisme, distinguer les competences regionales (Bruxelles, Wallonie, Flandre).",
    },
    "immobilier": {
        "jurisdiction": "Justice de paix / Tribunal de premiere instance",
        "sub_types": [
            "bail d'habitation",
            "bail commercial",
            "copropriete",
            "vente immobiliere",
            "vices caches",
            "servitudes",
        ],
        "deadlines": [
            {
                "name": "Action en garantie des vices caches",
                "duration": "Bref delai (apprecie par le juge)",
                "description": "Art. 1648 C. civ. — action a intenter a bref delai",
            },
            {
                "name": "Conge bail d'habitation",
                "duration": "6 mois / 3 mois selon le motif",
                "description": "Art. 3 §2-4 Loi sur les baux d'habitation — preavis selon le motif de conge",
            },
            {
                "name": "Renouvellement bail commercial",
                "duration": "Entre 18 et 15 mois avant l'echeance",
                "description": "Art. 14 Loi sur les baux commerciaux — demande de renouvellement",
            },
            {
                "name": "Delai d'appel",
                "duration": "1 mois",
                "description": "Art. 1051 C. jud.",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Contrat de bail ou acte de vente",
            "Etat des lieux d'entree (bail)",
            "Proces-verbal de copropriete (le cas echeant)",
            "Rapports d'expertise technique",
            "Correspondances et mises en demeure",
        ],
        "risk_points": [
            "Verifier l'enregistrement du bail (consequences fiscales et civiles)",
            "Analyser la conformite urbanistique du bien",
            "Evaluer les obligations du bailleur vs locataire",
            "Verifier les regles de copropriete (majorites requises, parties communes)",
            "Examiner la legislation regionale applicable (bail = competence regionale)",
        ],
        "legal_references": [
            "Code civil (art. 1714-1762 — bail)",
            "Legislation regionale sur le bail d'habitation (Bruxelles, Wallonie, Flandre)",
            "Loi du 30 avril 1951 sur les baux commerciaux",
            "Loi du 2 juin 2010 sur la copropriete",
        ],
        "strategy_notes": "Le droit du bail est regionalise en Belgique depuis 2014. "
        "Identifier la region competente (Bruxelles, Wallonie, Flandre) pour determiner les regles applicables. "
        "La justice de paix est competente pour les litiges locatifs (art. 591 C. jud.).",
    },
    "construction": {
        "jurisdiction": "Tribunal de premiere instance",
        "sub_types": [
            "responsabilite decennale",
            "malfacons",
            "retard de chantier",
            "architecte et entrepreneurs",
            "marches prives de travaux",
        ],
        "deadlines": [
            {
                "name": "Responsabilite decennale",
                "duration": "10 ans",
                "description": "Art. 1792 et 2270 C. civ. — responsabilite pour les gros ouvrages",
            },
            {
                "name": "Garantie des vices caches (construction)",
                "duration": "Bref delai (appreciation souveraine du juge)",
                "description": "Art. 1648 C. civ. — applicable aux malfacons cachees",
            },
            {
                "name": "Vices apparents",
                "duration": "A la reception provisoire",
                "description": "Jurisprudence — les reserves doivent etre emises lors de la reception provisoire",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Contrat d'entreprise / devis signe",
            "Plans et cahier des charges",
            "Proces-verbal de reception provisoire/definitive",
            "Rapport d'expertise technique",
            "Photos des malfacons",
            "Factures et preuves de paiement",
        ],
        "risk_points": [
            "Distinguer vices apparents (reception) et vices caches (bref delai)",
            "Identifier la responsabilite respective (architecte, entrepreneur, sous-traitant)",
            "Verifier les assurances professionnelles (loi Peeters-Borsus)",
            "Evaluer la necessite d'une expertise judiciaire",
            "Examiner les clauses limitatives de responsabilite",
        ],
        "legal_references": [
            "Code civil (art. 1787-1799 — contrat d'entreprise)",
            "Code civil (art. 1792 et 2270 — responsabilite decennale)",
            "Loi du 31 mai 2017 (Peeters-Borsus) — assurance responsabilite construction",
            "Loi du 9 mai 2019 (Peeters) — architectes et entrepreneurs",
        ],
        "strategy_notes": "En droit de la construction belge, la distinction entre reception provisoire et definitive est capitale. "
        "L'expertise judiciaire est souvent necessaire pour etablir les responsabilites techniques. "
        "Depuis 2018, l'assurance decennale est obligatoire (loi Peeters-Borsus).",
    },
    "societes": {
        "jurisdiction": "Tribunal de l'entreprise",
        "sub_types": [
            "constitution de societe",
            "responsabilite des administrateurs",
            "conflit entre associes",
            "dissolution et liquidation",
            "transformation de societe",
            "fusion et scission",
        ],
        "deadlines": [
            {
                "name": "Publication au Moniteur belge",
                "duration": "30 jours",
                "description": "Art. 2:7 CSA — publication des actes de societe",
            },
            {
                "name": "Depot des comptes annuels",
                "duration": "7 mois apres la cloture",
                "description": "Art. 3:12 CSA — depot aupres de la BNB",
            },
            {
                "name": "Action en responsabilite (administrateurs)",
                "duration": "5 ans",
                "description": "Art. 2:143 CSA — prescription de l'action en responsabilite",
            },
            {
                "name": "Exclusion/retrait d'associe",
                "duration": "Pas de delai fixe",
                "description": "Art. 2:63 et s. CSA — action en exclusion ou retrait devant le tribunal de l'entreprise",
            },
        ],
        "required_documents": [
            "Lettre de mandat signee",
            "Acte constitutif et statuts coordonnes",
            "Extrait BCE/KBO",
            "Comptes annuels des 3 derniers exercices",
            "Proces-verbaux des assemblees generales",
            "Convention d'actionnaires (le cas echeant)",
            "Registre des parts/actions",
        ],
        "risk_points": [
            "Verifier la conformite aux nouvelles dispositions du CSA (entree en vigueur 2020)",
            "Analyser les conflits d'interets des administrateurs (art. 5:76, 7:96 CSA)",
            "Evaluer la responsabilite des administrateurs (plafonds — art. 2:57 CSA)",
            "Verifier le respect de la procedure de sonnette d'alarme (art. 5:153, 7:228 CSA)",
            "Examiner les droits des actionnaires minoritaires",
        ],
        "legal_references": [
            "Code des societes et des associations (CSA) du 23 mars 2019",
            "Code judiciaire (art. 574 — competence du tribunal de l'entreprise)",
            "Loi du 16 mars 1803 — organisation du notariat",
            "Arrete royal du 29 avril 2019 — execution du CSA",
        ],
        "strategy_notes": "Le CSA a profondement reforme le droit des societes belge depuis 2020. "
        "La SRL (ancienne SPRL) est la forme de droit commun avec une grande liberte statutaire. "
        "Les plafonds de responsabilite des administrateurs (art. 2:57 CSA) sont une nouveaute majeure.",
    },
}


def estimate_complexity(description: str, matter_type: str) -> str:
    """Estimate case complexity based on description analysis."""
    desc_lower = description.lower()
    complex_indicators = [
        "international",
        "transfrontalier",
        "multi-parties",
        "expertise",
        "cassation",
        "europeen",
        "constitutionnel",
        "class action",
        "groupe de societes",
        "fusion",
        "scission",
    ]
    simple_indicators = [
        "recouvrement",
        "injonction",
        "simple",
        "consentement mutuel",
        "non conteste",
        "amiable",
        "reconnaissance",
    ]

    complex_count = sum(1 for ind in complex_indicators if ind in desc_lower)
    simple_count = sum(1 for ind in simple_indicators if ind in desc_lower)

    if complex_count >= 2 or matter_type in ("administrative",):
        return "complex"
    if simple_count >= 2:
        return "simple"
    if complex_count >= 1:
        return "complex"
    if simple_count >= 1:
        return "simple"
    return "moderate"
