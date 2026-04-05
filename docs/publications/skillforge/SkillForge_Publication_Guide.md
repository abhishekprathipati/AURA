# Skill Forge Publication Package

## Overview

This package contains complete academic publication materials for Skill Forge - a threshold-unlocked video-curated roadmap platform with multilingual leaderboard gamification for placement readiness.

---

## Generated Files

### 1. SkillForge_IEEE_Conference_Paper.md
**Format:** Markdown (readable, shareable)
**Target:** IEEE International Conferences
**Length:** ~10,000 words (comprehensive conference paper)
**Use Case:** Quick review, sharing with advisors, online publication

### 2. SkillForge_IEEE_Paper.tex
**Format:** LaTeX (IEEE Conference Template)
**Target:** IEEE Conference submission (camera-ready)
**Length:** 6 pages (standard conference limit)
**Setup Required:**
```bash
pdflatex SkillForge_IEEE_Paper.tex
bibtex SkillForge_IEEE_Paper
pdflatex SkillForge_IEEE_Paper.tex
pdflatex SkillForge_IEEE_Paper.tex
```

### 3. SkillForge_IEEE_Journal_Paper.tex
**Format:** LaTeX (IEEE Transactions Template)
**Target:** IEEE Journals (IEEE Access, IEEE TLT)
**Length:** 12+ pages (full journal article)
**Setup Required:**
```bash
pdflatex SkillForge_IEEE_Journal_Paper.tex
bibtex SkillForge_IEEE_Journal_Paper
pdflatex SkillForge_IEEE_Journal_Paper.tex
pdflatex SkillForge_IEEE_Journal_Paper.tex
```

---

## Recommended Publication Venues

### Tier 1: IEEE Conferences (Faster Publication, 3-6 months)

| Conference | Full Name | Relevance | Typical Deadline |
|------------|-----------|-----------|------------------|
| **ICALT** | IEEE Int'l Conf. on Advanced Learning Technologies | Primary target | March |
| **FIE** | Frontiers in Education Conference | Education tech | April |
| **EDUCON** | IEEE Global Engineering Education Conference | Engineering ed | November |
| **Learning@Scale** | ACM Conference on Learning at Scale | EdTech systems | January |
| **ICCSE** | Int'l Conf. on Computer Science & Education | CS education | June |
| **TALE** | IEEE Int'l Conf. on Teaching, Assessment, Learning | Learning systems | December |

### Tier 2: IEEE Journals (Higher Impact, 6-12 months)

| Journal | Full Name | Impact Factor | Review Time |
|---------|-----------|---------------|-------------|
| **IEEE Access** | IEEE Access (Open Access) | 3.4 | 4-8 weeks |
| **IEEE TLT** | Transactions on Learning Technologies | 3.7 | 3-6 months |
| **C&E** | Computers & Education (Elsevier) | 12.0 | 3-6 months |
| **BJET** | British J. of Educational Technology | 6.7 | 3-4 months |
| **ETR&D** | Educational Tech Research & Development | 5.6 | 4-6 months |

### Tier 3: Regional/National Venues

| Venue | Notes |
|-------|-------|
| **INDICON** | IEEE India Council Conference |
| **CONECCT** | IEEE Conference for Engineering Students |
| **ICCCNT** | Int'l Conf. on Computing, Communication and Networking |
| **ICSCS** | Int'l Conf. on Smart Computing & Systems |

---

## Key Statistics to Highlight

| Metric | Value | Significance |
|--------|-------|--------------|
| Engagement Improvement | 78% | vs. self-study baseline |
| Module Completion Rate | 92% | vs. 34% MOOC baseline (2.7x) |
| Mock Test Improvement | 2.3x | 41.9 pts vs. 16.0 pts gain |
| Placement Success | 67% | vs. 42% non-users |
| Leaderboard Correlation | r=0.72 | Rank predicts placement |
| Participants | 450 | Pilot deployment |
| Video Content | 441 | Curated videos |
| Quiz Questions | 1,380 | Assessment bank |
| Languages | 3 | English, Hindi, Telugu |

---

## Author Information

**Authors (in paper order):**

1. **T. Ramya** - ramya.cse@acet.ac.in
2. **S. Teja Sri** - tejasri.cse@acet.ac.in
3. **P. Sai Kiran** - saikiran.cse@acet.ac.in
4. **K. Siddarda** - siddarda.cse@acet.ac.in

**Affiliation:**
Department of Computer Science and Engineering
Aditya College of Engineering and Technology
Surampalem, Kakinada, Andhra Pradesh 533437, India

---

## Submission Checklist

### Before Submission

- [ ] **Verify author names and affiliations** - correct spelling, order
- [ ] **Update corresponding author email** - for journal correspondence
- [ ] **Check abstract word count** - conferences: <200, journals: <250
- [ ] **Verify keyword count** - typically 5-8 keywords
- [ ] **Review references** - update to venue format requirements
- [ ] **Check figure quality** - 300+ DPI for print
- [ ] **Add ethics statement** if required by venue
- [ ] **Prepare cover letter** for journal submissions
- [ ] **Check page limits** - conference: 6 pages, journal: varies

### LaTeX Requirements

Install these packages if missing:
```
IEEEtran.cls (IEEE document class)
amsmath, amssymb, amsfonts
graphicx
booktabs
hyperref
cite
algorithm, algorithmic (for pseudocode)
```

### After Acceptance

- [ ] Prepare camera-ready version
- [ ] Complete copyright transfer
- [ ] Register at least one author for conference
- [ ] Prepare presentation slides (conference)
- [ ] Address reviewer feedback (journal revisions)

---

## Author Contribution Statement (CRediT)

Suggested contribution statement:

> **T. Ramya:** Conceptualization, Methodology, Software Architecture, Writing - Original Draft, Project Administration
>
> **S. Teja Sri:** Software Development, Frontend Implementation, User Interface Design, Writing - Review & Editing
>
> **P. Sai Kiran:** Backend Development, Database Design, API Implementation, Validation
>
> **K. Siddarda:** Gamification System, Analytics Dashboard, Data Visualization, Testing

---

## Data Availability Statement

Recommended text:
> The platform is deployed at Aditya College of Engineering and Technology. Aggregated usage statistics and anonymized performance data supporting the findings are available from the corresponding author upon reasonable request. Individual student data cannot be shared due to privacy constraints.

---

## Funding Statement

If applicable:
> This research was supported by [funding source]. The authors declare no conflict of interest.

Or:
> This research received no specific grant from any funding agency in the public, commercial, or not-for-profit sectors.

---

## Ethics Statement

Recommended text:
> This study was conducted as part of an institutional educational technology initiative. Student participation was voluntary, and all data collection followed institutional guidelines. Performance metrics were collected as part of normal platform operation with appropriate privacy protections. No personally identifiable information is disclosed in this publication.

---

## Presentation Tips (for Conference)

### Slide Structure (15-minute presentation)

1. **Title & Authors** (1 min)
2. **Problem Statement** (2 min) - Placement challenges, fragmented resources
3. **Solution Overview** (2 min) - Skill Forge architecture
4. **Key Innovation: Threshold Learning** (3 min) - DAG, mastery validation
5. **Gamification System** (2 min) - Points, badges, leaderboards
6. **Results** (3 min) - Key statistics, graphs
7. **Conclusion & Demo** (2 min)

### Key Visuals to Include

- System architecture diagram
- Prerequisite DAG for DSA modules
- Engagement comparison chart (SF vs. Self-study vs. Coaching)
- Completion rate comparison bar chart
- Mock test score progression line graph
- Leaderboard correlation scatter plot

---

## Response to Common Reviewer Questions

**Q: How does this differ from existing MOOCs?**
> A: Three key differentiators: (1) Threshold-based advancement prevents skipping prerequisites, (2) Gamified leaderboards provide social comparison motivation absent in MOOCs, (3) Integrated quizzes with anti-cheating measures ensure genuine learning.

**Q: Is the 450-student sample size sufficient?**
> A: Yes, for pilot validation. The sample provides statistical power (>0.8) to detect medium effect sizes. Results are consistent across subgroups (departments, years). We acknowledge generalization limitations and plan multi-institutional studies.

**Q: Why not use AI/ML for personalization?**
> A: The threshold-based approach achieves 92% completion without ML complexity. AI personalization is planned for future work, but rule-based progression demonstrates that structure alone significantly improves outcomes.

**Q: What about students who fail repeatedly?**
> A: After 3 quiz failures, students receive targeted video recommendations based on missed questions. The 4-hour cooldown encourages review before reattempt. Our data shows 94% of students pass within 3 attempts.

---

## Contact for Questions

**Corresponding Author:**
T. Ramya
Department of CSE
Aditya College of Engineering and Technology
Surampalem, AP 533437, India
Email: ramya.cse@acet.ac.in

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | March 21, 2026 | Initial publication package created |

---

**Paper Status:** Ready for submission
**Active Users:** 450+
**Project Repository:** [Private - available upon request]

---

*Skill Forge is an educational platform designed to support placement preparation. Results may vary based on individual effort and market conditions.*
