# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.

Each owner manages one schedule and can have multiple pets. Each pet requires multiple tasks, and the schedule contains all tasks. This structure enables the app to assign, track, and prioritize pet care activities for each owner's pets.

- What classes did you include, and what responsibilities did you assign to each?

**Task** — Represents a pet care task with priority and due date. Can mark itself as complete, tracks recurrence frequency, and supports time-based sorting for schedule ordering.

**Pet** — Represents a pet with its attributes and care information. Returns the type of animal, its specific care needs, and the priority level for this pet's care. Holds a list of tasks assigned to it.

**Scheduler** (originally called Schedule) — Manages a calendar of tasks for pet care. Sorts tasks by time, filters by pet or status, detects same-time conflicts, expands recurring tasks across time windows, and displays the current schedule.

**Owner** — Represents a pet owner with basic information. Holds a list of pets and aggregates all tasks across pets for the scheduler.

**KnowledgeBase** (added in Module 4) — The RAG retrieval component. Stores breed-specific pet care data and returns it with a confidence score so the AI agent knows how reliable its source data is.

**PawPalAgent** (added in Module 4) — The agentic AI assistant. Follows a plan-retrieve-generate-validate workflow to produce personalized care plans grounded in knowledge base data.

**b. Design changes**

- Did your design change during implementation?

Yes, significantly across both phases.

- If yes, describe at least one change and why you made it.

In Module 2-3, I added a `completion_status` field to the Task class so owners could track which tasks were done, and added recurring task logic so completing a daily task auto-generates the next occurrence. I also changed the Schedule class to a Scheduler class that works through the Owner rather than standing alone, because it made more sense for the scheduler to pull tasks from all pets via the owner.

In Module 4, I added two entirely new classes: `KnowledgeBase` for RAG retrieval and `PawPalAgent` for the agentic workflow. The original system was purely rule-based — you added tasks manually and the scheduler organized them. The new design lets the AI generate task recommendations grounded in breed-specific data, which fundamentally changed how the app works. The key design decision was keeping the original Scheduler untouched and having the AI agent feed suggestions *through* it, so all the existing conflict detection and sorting still applies to AI-generated tasks.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider?

Time (tasks are sorted chronologically), frequency (daily/weekly/monthly/yearly recurrence), conflict detection (flags tasks scheduled at the same time), and pet assignment (each task belongs to a specific pet so multi-pet households stay organized).

- How did you decide which constraints mattered most?

By looking at the requirements in the README and thinking about what a real pet owner would need. Time sorting was the most important because a daily schedule that isn't in order is useless. Conflict detection came next because a single owner can't walk the dog and clean the litter box at the same time.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

The system uses a local JSON knowledge base instead of a real vector database or external API. This means breed coverage is limited to what's manually entered, but it makes the project fully reproducible — anyone can clone the repo and run it without setting up a database or getting API keys for a pet care service.

- Why is that tradeoff reasonable for this scenario?

For a class project, reproducibility matters more than completeness. A system that works reliably for 10 breeds is more valuable to demonstrate than one that theoretically covers 300 breeds but requires a database server, API keys, and internet access to function. The confidence scoring system also makes this tradeoff transparent — the user sees a score of 0.10 for an unsupported species instead of getting silently bad advice.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project?

Design, brainstorming, debugging, and code generation. In Module 4, I used Claude to help architect the RAG knowledge base, build the agentic workflow in `ai_agent.py`, create the reliability test suite, and generate the system architecture diagram. The collaboration was iterative — I described what I needed, reviewed the output, tested it, and went back with corrections.

- What kinds of prompts or questions were most helpful?

"Explain to me how..." for understanding concepts. "By looking at this code and comparing with the diagram, do you see any match?" for verification. In Module 4, the most useful prompt pattern was giving Claude my existing code and asking it to build new features that integrate with what I already had, rather than starting from scratch.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.

Two instances stand out. First, when it came to the initial UML diagram in Module 2, I reworked the design because the AI's version didn't match how I wanted the classes to relate. Second, early in Module 4, Claude generated a `git push` command pointing to a repository URL that didn't exist yet on GitHub. The command failed with "repository not found," and I had to figure out that I needed to create the empty repository on GitHub's website first before pushing. The AI assumed the repo already existed, which isn't how GitHub works.

- How did you evaluate or verify what the AI suggested?

I read the answers provided, applied logical thinking, and tested everything. For code, I ran the test suite and checked that outputs made sense. For the git issue, the error message itself told me what was wrong. The key lesson was that AI gives you syntactically correct commands that can still fail because of assumptions about your environment.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

In Module 2-3: 38 pytest cases covering recurring tasks (daily, weekly, monthly, yearly), time-based sorting, conflict detection, filtering by pet and status, time window queries, and edge cases like February date adjustments.

In Module 4: 40 additional reliability tests across four categories:
1. **Automated tests** — Knowledge base retrieval accuracy, breed-specific vs. default fallback behavior, case insensitivity, whitespace handling, and task field validation.
2. **Confidence scoring** — Verified the AI rates itself correctly: 0.87 for known breeds, 0.55 for species-only, 0.10 for unknown species.
3. **Logging and error handling** — Confirmed every agent action is logged with timestamps and processing time, and that empty schedules and unknown inputs return graceful responses instead of crashes.
4. **Output quality (human evaluation)** — Checked that care plans mention breed-specific health info, cover all care categories (exercise, feeding, grooming, health), suggest valid task times, and don't recommend inappropriate activities (like walks for cats).

- Why were these tests important?

The scheduling tests ensure the core logic is deterministic and correct — a bug in recurring task generation could cause missed feedings. The AI reliability tests prove the system knows when it's uncertain (confidence scoring), handles edge cases without crashing (error handling), and produces advice that's actually grounded in the knowledge base rather than hallucinated (output quality checks).

**Testing summary:** 40 out of 40 tests passed. Confidence scores averaged 0.51 across all scenarios; accuracy improved significantly with breed-specific data (0.87) compared to generic species defaults (0.55). The AI correctly identified when it lacked knowledge, scoring only 0.10 for unknown species. Conflict detection caught all overlapping tasks.

**b. Confidence**

- How confident are you that your scheduler works correctly?

8/10 for the core scheduler (well-tested, deterministic). 7/10 for the AI agent (confidence scoring works well, but knowledge base coverage is limited).

- What edge cases would you test next if you had more time?

I would test the Streamlit `app.py` integration end-to-end, add tests for multi-pet household scheduling (3+ pets), test what happens when the AI suggests tasks that conflict with manually-added ones, and add stress tests with large numbers of tasks to check performance.

---

## 5. Reflection and Ethics

**a. What went well**

The confidence scoring system. Seeing the concrete numbers (0.87 for known breeds vs. 0.10 for unknown species) made the quality gap visible in a way that just reading the output never would. It also gave me a testing hook — I could write automated checks that verify the AI knows when it's uncertain, which is hard to test otherwise.

**b. What you would improve**

I would add a vector database (like ChromaDB) to replace the static JSON knowledge base so the system could handle any breed without manual data entry. I would also add session persistence so the AI remembers past interactions, and build an evaluation framework that scores AI outputs against a rubric automatically instead of relying on manual checks.

**c. Key takeaway**

When designing a system with AI, as a developer, AI should not be the one taking over — I should use it to make the design better instead. Module 4 reinforced this: the AI agent recommends, but the human decides. The system is designed so that AI suggestions always pass through the deterministic scheduler and always require human approval before becoming active tasks.

**d. Limitations and biases in the system**

The knowledge base only covers popular Western pet breeds. Someone with a Shiba Inu, a Maine Coon, or a bearded dragon gets generic advice at best. This is an implicit bias — common breeds get a high-quality experience while less mainstream pets are underserved. The system also assumes a single-owner household, so it flags two tasks at the same time as a conflict even though two people in the same home could handle them simultaneously.

All care recommendations are general best practices, not tailored to individual pet health. A Golden Retriever with arthritis needs a different exercise plan than a healthy one, but the system treats them identically.

**e. Could the AI be misused, and how would you prevent that?**

The most realistic risk is over-reliance. The system uses specific medical language ("prone to hip dysplasia," "risk of bloat") that sounds authoritative, and someone might skip a vet visit because PawPal+ already told them what to watch for. To prevent this, health notes always recommend professional checkups, the confidence score is visible so users can see uncertainty, and the human-in-the-loop design means no AI suggestion becomes an active task without manual approval.

**f. What surprised you while testing reliability?**

The biggest surprise was how much the confidence scores revealed. I assumed species-level defaults would be "good enough," but seeing the score drop from 0.87 to 0.55 made the quality gap concrete — 0.55 means the system is barely confident in its own advice. That number forced me to take knowledge base gaps seriously and add the fallback warnings.

I was also surprised by how many ways "empty input" can break things. An owner with no pets, a pet with no tasks, a breed name that's just whitespace — each is a different failure path, and testing them caught three bugs in early versions where the agent would crash instead of returning a helpful error message.

**g. AI collaboration — one helpful suggestion, one flawed suggestion**

**Helpful:** When designing the confidence scoring formula, Claude suggested weighting retrieval confidence at 50%, task completeness at 30%, breed specificity at 10%, with warnings applying up to a 20% penalty. This produced scores that matched my intuition about output quality, and the formula was easy to explain and test. I wouldn't have arrived at those weights as quickly on my own.

**Flawed:** The `git push` to a nonexistent repository. Claude gave me a perfectly formatted command that failed because the target repo hadn't been created on GitHub yet. It was a reminder that AI can produce correct-looking commands based on assumptions it can't verify about your environment. After that, I started double-checking setup steps against the actual state of my tools before running them.