def match_score(unlocked_skill, opportunity):
    if unlocked_skill is None:
        return 0
    skills = list(opportunity.skills.all())
    if not skills:
        return 0
    return round(
        sum(skill.pk == unlocked_skill.pk for skill in skills) * 100 / len(skills)
    )
