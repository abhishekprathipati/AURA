# AURA Publication Package

## Overview

This package contains complete academic publication materials for the AURA (Adaptive Understanding and Response Architecture) student mental wellness platform. The materials are prepared for submission to IEEE conferences and journals.

---

## Generated Files

### 1. AURA_IEEE_Conference_Paper.md
**Format:** Markdown (readable, shareable)
**Target:** IEEE International Conferences (ICALT, FIE, EDUCON, COMPSAC)
**Length:** ~8,000 words (suitable for 10-page conference paper)
**Use Case:** Quick review, sharing with advisors, online publication

### 2. AURA_IEEE_Paper.tex
**Format:** LaTeX (IEEE Conference Template)
**Target:** IEEE Conference submission (camera-ready)
**Length:** 6 pages (standard conference limit)
**Setup Required:**
- Install TeX distribution (TeX Live, MiKTeX)
- Compile with `pdflatex AURA_IEEE_Paper.tex`

### 3. AURA_IEEE_Journal_Paper.tex
**Format:** LaTeX (IEEE Transactions Template)
**Target:** IEEE Journals (IEEE Access, IEEE TLT, IEEE TETC)
**Length:** 12+ pages (full journal article)
**Setup Required:**
- Install TeX distribution
- Compile with `pdflatex AURA_IEEE_Journal_Paper.tex`

### 4. AURA_Project_Paper.md (Existing)
**Format:** Markdown
**Purpose:** Technical documentation, project reference

---

## Recommended Publication Venues

### Tier 1: IEEE Conferences (Faster Publication)

| Conference | Full Name | Relevance | Deadline (Typical) |
|------------|-----------|-----------|-------------------|
| **ICALT** | IEEE International Conference on Advanced Learning Technologies | Primary target | March |
| **FIE** | Frontiers in Education Conference | Education tech focus | April |
| **EDUCON** | IEEE Global Engineering Education Conference | Educational innovation | November |
| **COMPSAC** | IEEE Annual Computer Software and Applications Conference | Software systems | February |
| **ICCSE** | International Conference on Computer Science & Education | CS education | June |

### Tier 2: IEEE Journals (Higher Impact)

| Journal | Full Name | Impact Factor | Review Time |
|---------|-----------|---------------|-------------|
| **IEEE Access** | IEEE Access (Open Access) | 3.4 | 4-8 weeks |
| **IEEE TLT** | IEEE Transactions on Learning Technologies | 3.7 | 3-6 months |
| **IEEE TETC** | IEEE Transactions on Emerging Topics in Computing | 5.9 | 4-8 months |

### Tier 3: Other Venues

| Venue | Notes |
|-------|-------|
| **ACM CHI** | Human-Computer Interaction focus |
| **JMIR Mental Health** | Mental health technology |
| **Computers & Education** | Educational computing |

---

## Submission Checklist

### Before Submission

- [ ] **Author Information:** Verify all author names, affiliations, and emails
- [ ] **Abstract:** Under 200 words for conferences, 250 words for journals
- [ ] **Keywords:** 5-8 relevant terms
- [ ] **References:** Update citation formats per venue requirements
- [ ] **Figures:** Ensure high resolution (300+ DPI)
- [ ] **Ethics Statement:** Add if required by venue

### LaTeX Compilation

```bash
# For conference paper
pdflatex AURA_IEEE_Paper.tex
bibtex AURA_IEEE_Paper
pdflatex AURA_IEEE_Paper.tex
pdflatex AURA_IEEE_Paper.tex

# For journal paper
pdflatex AURA_IEEE_Journal_Paper.tex
bibtex AURA_IEEE_Journal_Paper
pdflatex AURA_IEEE_Journal_Paper.tex
pdflatex AURA_IEEE_Journal_Paper.tex
```

### Required LaTeX Packages

Install these packages if not present:
- `IEEEtran.cls` (IEEE document class)
- `amsmath`, `amssymb`, `amsfonts`
- `graphicx`
- `booktabs`
- `hyperref`
- `cite`

---

## Key Statistics to Highlight

| Metric | Value | Significance |
|--------|-------|--------------|
| Variance Reduction | 92% | EMA + Logistic stabilization |
| Manipulation Suppression | 22% | Burst detection effectiveness |
| Confidence Range | 0.15-0.77 | Calibrated uncertainty |
| Crisis Detection | 3-5 readings | Timely intervention |
| Signal Count | 6 | Multi-dimensional assessment |
| API Endpoints | 137 | Complete platform |

---

## Author Contribution Statement

Suggested text for CRediT (Contributor Roles Taxonomy):

> **Abhishek Prathipati:** Conceptualization, Methodology, Software, Writing - Original Draft, Project Administration
>
> **Harika Padala:** Software, Visualization, User Interface Design, Writing - Review & Editing
>
> **Teja Srinivas Dasari:** Software, AI Integration, Validation, Writing - Review & Editing
>
> **Sowjanya Guttula:** Data Curation, Database Design, Investigation, Writing - Review & Editing

---

## Funding Statement

Add if applicable:
> This work was supported by [Funding Source]. The authors declare no conflict of interest.

Or:
> This research received no specific grant from any funding agency.

---

## Data Availability Statement

Recommended text:
> The synthetic evaluation data and algorithm implementations are available at [GitHub repository URL]. Real student data cannot be shared due to privacy and ethical constraints.

---

## Ethics Statement

Recommended text:
> AURA is designed as a behavioral wellness estimation tool and does not constitute medical or psychological diagnosis. The platform includes appropriate disclaimers and encourages professional evaluation when indicated. Synthetic archetypes were used for evaluation to avoid ethical constraints of real student mental health data. The platform is deployed with institutional approval and includes comprehensive privacy protections.

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | March 21, 2026 | Initial publication package created |

---

## Contact Information

For submissions and correspondence:

**Corresponding Author:**
Abhishek Prathipati
Department of CSE - AI & ML
Aditya College of Engineering and Technology
Surampalem, Andhra Pradesh 533437, India
Email: abhishek.cse@acet.ac.in

---

## Quick Start for Submission

1. **Choose your venue** from the recommended list above
2. **Select the appropriate file:**
   - Conference: `AURA_IEEE_Paper.tex`
   - Journal: `AURA_IEEE_Journal_Paper.tex`
3. **Compile to PDF** using LaTeX
4. **Review formatting** against venue guidelines
5. **Submit** via the venue's submission portal

Good luck with your publication!
