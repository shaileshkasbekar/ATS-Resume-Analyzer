def calculate_ats_score(resume_skills, role_skill_groups):
    """
    Generic dynamic ATS scoring engine.

    Technology groups are treated as alternative paths.
    Common groups are evaluated separately.

    Core / supporting / optional skills are evaluated
    using their database weights.

    Technology path detection considers:
    1. Weighted skill score
    2. Number of matched skills
    3. Core skill matches
    """

    # -----------------------------------------
    # Normalize resume skills
    # -----------------------------------------

    resume_skills = {
        skill.strip().lower()
        for skill in resume_skills
        if skill.strip()
    }

    # -----------------------------------------
    # Store groups
    # -----------------------------------------

    group_results = {}

    # -----------------------------------------
    # Build group structure
    # -----------------------------------------

    for skill_data in role_skill_groups:

        group_name = skill_data["group_name"]

        skill_name = skill_data["skill_name"]

        importance = skill_data["importance"]

        weight = float(
            skill_data["weight"]
        )

        group_type = skill_data["group_type"]

        if group_name not in group_results:

            group_results[group_name] = {
                "group_type": group_type,
                "total_weight": 0,
                "matched_weight": 0,
                "matched_skills": [],
                "missing_skills": [],
                "core_total": 0,
                "core_matched": 0,
                "supporting_total": 0,
                "supporting_matched": 0,
                "optional_total": 0,
                "optional_matched": 0,
                "score": 0
            }

        # -----------------------------------------
        # Add total weight
        # -----------------------------------------

        group_results[group_name][
            "total_weight"
        ] += weight


        # -----------------------------------------
        # Store tier information
        # -----------------------------------------

        if importance == "core":

            group_results[group_name][
                "core_total"
            ] += weight

        elif importance == "supporting":

            group_results[group_name][
                "supporting_total"
            ] += weight

        elif importance == "optional":

            group_results[group_name][
                "optional_total"
            ] += weight


        # -----------------------------------------
        # Skill matching
        # -----------------------------------------

        if (
            skill_name.strip().lower()
            in resume_skills
        ):

            group_results[group_name][
                "matched_weight"
            ] += weight

            group_results[group_name][
                "matched_skills"
            ].append(
                skill_name
            )


            # -------------------------------------
            # Store matched tier
            # -------------------------------------

            if importance == "core":

                group_results[group_name][
                    "core_matched"
                ] += weight

            elif importance == "supporting":

                group_results[group_name][
                    "supporting_matched"
                ] += weight

            elif importance == "optional":

                group_results[group_name][
                    "optional_matched"
                ] += weight

        else:

            group_results[group_name][
                "missing_skills"
            ].append(
                skill_name
            )


    # -----------------------------------------
    # Calculate each group score
    # -----------------------------------------

    for group_name, group in group_results.items():

        total_weight = group[
            "total_weight"
        ]

        matched_weight = group[
            "matched_weight"
        ]


        if total_weight > 0:

            group["score"] = round(
                (
                    matched_weight /
                    total_weight
                ) * 100,
                2
            )

        else:

            group["score"] = 0


    # -----------------------------------------
    # Separate common and technology groups
    # -----------------------------------------

    common_groups = {}

    technology_groups = {}


    for group_name, group in group_results.items():

        if group["group_type"] == "common":

            common_groups[group_name] = group

        elif group["group_type"] == "technology":

            technology_groups[group_name] = group


    # -----------------------------------------
    # Find strongest technology path
    # -----------------------------------------
    #
    # Do NOT simply choose the highest percentage.
    #
    # A path with one matched skill should not
    # automatically beat a path with several
    # important matched skills.
    #
    # Path strength considers:
    #
    # 60% → weighted skill score
    # 30% → number of matched skills
    # 10% → core skill score
    #
    # -----------------------------------------

    detected_path = None

    strongest_path_score = 0


    # Find maximum number of skills in any path

    max_path_skills = 0

    for group in technology_groups.values():

        total_skills = (
            len(group["matched_skills"])
            +
            len(group["missing_skills"])
        )

        if total_skills > max_path_skills:

            max_path_skills = total_skills


    for group_name, group in technology_groups.items():

        matched_count = len(
            group["matched_skills"]
        )

        total_count = (
            matched_count
            +
            len(group["missing_skills"])
        )


        # -------------------------------------
        # No matched skills = not a path
        # -------------------------------------

        if matched_count == 0:

            continue


        # -------------------------------------
        # Weighted score
        # -------------------------------------

        weighted_score = group["score"]


        # -------------------------------------
        # Match coverage
        # -------------------------------------

        if total_count > 0:

            match_coverage = (
                matched_count /
                total_count
            ) * 100

        else:

            match_coverage = 0


        # -------------------------------------
        # Core skill score
        # -------------------------------------

        if group["core_total"] > 0:

            core_score = (
                group["core_matched"] /
                group["core_total"]
            ) * 100

        else:

            # If a group has no core skills,
            # don't penalize it.

            core_score = weighted_score


        # -------------------------------------
        # Path strength
        # -------------------------------------

        path_strength = (

            weighted_score * 0.60

            +

            match_coverage * 0.30

            +

            core_score * 0.10

        )


        path_strength = round(
            path_strength,
            2
        )


        # -------------------------------------
        # Select strongest path
        # -------------------------------------

        if path_strength > strongest_path_score:

            strongest_path_score = path_strength

            detected_path = group_name


    # -----------------------------------------
    # Calculate Common Score
    # -----------------------------------------

    common_total_weight = 0

    common_matched_weight = 0


    for group in common_groups.values():

        common_total_weight += (
            group["total_weight"]
        )

        common_matched_weight += (
            group["matched_weight"]
        )


    if common_total_weight > 0:

        common_score = (
            common_matched_weight /
            common_total_weight
        ) * 100

    else:

        common_score = 0


    common_score = round(
        common_score,
        2
    )


    # -----------------------------------------
    # Overall Rule-Based Score
    # -----------------------------------------

    if detected_path:

        # Common skills = 40%
        # Technology path = 60%

        overall_score = (

            common_score * 0.40

            +

            strongest_path_score * 0.60

        )

    else:

        overall_score = common_score


    overall_score = round(
        overall_score,
        2
    )


    # -----------------------------------------
    # Matched Skills
    # -----------------------------------------

    matched_skills = []


    for group in group_results.values():

        for skill in group[
            "matched_skills"
        ]:

            matched_skills.append(
                skill
            )


    # -----------------------------------------
    # Missing Skills
    # -----------------------------------------
    #
    # Only include:
    #
    # 1. Common groups
    # 2. Detected technology path
    #
    # Alternative technology paths
    # are NOT treated as missing.
    #
    # -----------------------------------------

    missing_skills = []


    for group in common_groups.values():

        for skill in group[
            "missing_skills"
        ]:

            missing_skills.append(
                skill
            )


    if detected_path:

        detected_group = (
            technology_groups[
                detected_path
            ]
        )


        for skill in detected_group[
            "missing_skills"
        ]:

            missing_skills.append(
                skill
            )


    # -----------------------------------------
    # Recommendations
    # -----------------------------------------

    recommended_skills = []


    # -----------------------------------------
    # Common recommendations
    # -----------------------------------------

    for skill_data in role_skill_groups:

        group_name = skill_data[
            "group_name"
        ]

        if group_name not in common_groups:

            continue


        skill_name = skill_data[
            "skill_name"
        ]

        importance = skill_data[
            "importance"
        ]


        if (

            skill_name.strip().lower()
            not in resume_skills

            and

            importance in [
                "core",
                "supporting"
            ]

        ):

            recommendation = (
                "Learn " + skill_name
            )


            if (
                recommendation
                not in recommended_skills
            ):

                recommended_skills.append(
                    recommendation
                )


    # -----------------------------------------
    # Technology path recommendations
    # -----------------------------------------

    if detected_path:

        for skill_data in role_skill_groups:

            if (
                skill_data["group_name"]
                != detected_path
            ):

                continue


            skill_name = skill_data[
                "skill_name"
            ]

            importance = skill_data[
                "importance"
            ]


            if (

                skill_name.strip().lower()
                not in resume_skills

                and

                importance in [
                    "core",
                    "supporting"
                ]

            ):

                recommendation = (
                    "Learn " + skill_name
                )


                if (
                    recommendation
                    not in recommended_skills
                ):

                    recommended_skills.append(
                        recommendation
                    )


    # -----------------------------------------
    # Remove duplicates
    # -----------------------------------------

    matched_skills = list(
        dict.fromkeys(
            matched_skills
        )
    )


    missing_skills = list(
        dict.fromkeys(
            missing_skills
        )
    )


    recommended_skills = list(
        dict.fromkeys(
            recommended_skills
        )
    )


    # -----------------------------------------
    # Add common score to groups
    # -----------------------------------------

    for group_name, group in common_groups.items():

        group["category_score"] = (
            common_score
        )


    # -----------------------------------------
    # Add path strength
    # -----------------------------------------

    for group_name, group in technology_groups.items():

        if group_name == detected_path:

            group["path_strength"] = (
                strongest_path_score
            )

        else:

            group["path_strength"] = (
                group["score"]
            )


    # -----------------------------------------
    # Return
    # -----------------------------------------

    return (

        overall_score,

        matched_skills,

        missing_skills,

        recommended_skills,

        group_results,

        detected_path

    )