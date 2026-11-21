# Reviewing an adapter PR

The first reviewer follows a task from the upstream benchmark through generation and grading. The second reviewer checks the evidence and decides whether it supports merging the reviewed revision. The author runs the agreed parity experiment.

Track each incoming PR, including WIPs, in the review tracker. Record the PR, benchmark, stage, first and second reviewers, reviewed commit, evidence links, and who owns the next action. Update the row when the PR changes hands. Use the stages below.

## 1. Run the bot and read its comments

Trigger `/review-adapter` on the PR. Open the report and its coverage table, and check which revision and files it covered. The first reviewer reads each finding, opens the relevant code, and decides whether it needs a fix, was already addressed, or does not apply. If structural validation stopped the run, record that the code review was skipped and rerun it when the missing items are ready. If the missing item is the parity result itself, start the upstream and oracle checks while the author prepares the experiment.

## 2. Compare the adapter with upstream

Pin the upstream revision. Follow a concrete task through each distinct generation or grading path.

- **Task setup.** Compare what the agent actually sees: instructions, data split, tools, initial files, and limits. Can it do the same work with the same information?
- **Environment.** Inspect the generated code, images and services. When the adapter simulates an upstream dependency, check the behavior the task relies on.
- **Verifier.** Trace the agent's submission into the grading program. Compare its criteria, weights, partial credit, and failure handling with the upstream rubric. An unavailable service or judge can leave a trial unscored even when a wrong answer legitimately earns zero. Check both paths where relevant.
- **Separate verifier.** Expect new tasks to use a separate verifier on the [latest stable Harbor release](https://github.com/harbor-framework/harbor/releases/latest). Inspect a generated task and check what actually crosses into the grading environment. If scoring depends on live state, ask how that state is preserved and agree on any exception with a maintainer.
- **README.** Read it as someone trying to run the adapter for the first time. Can you find the command, the dataset revision, what changed from upstream, and which tasks, agents and judges the results cover? Ask for a specific edit where an omission changes how readers would interpret a score.

An agent can help locate upstream code, summarize a diff, or trace an artifact. The reviewer opens the sources, checks the behavior, and writes the finding in their own words. Give the author a concrete example and explain what would settle it.

## 3. Generate tasks and run the oracle

From the reviewed commit, use the documented adapter command to generate tasks into an empty directory. Compare generated task IDs and file contents with the pinned dataset PR. Check missing, extra, and changed files. If the dataset was built from an earlier revision, establish which change explains the difference. Ask the author to regenerate stale output when the adapter is correct. Fix the adapter first when the generated behavior is wrong.

Run the reference solution on the newly generated tasks with the latest stable Harbor. Run small datasets in full. For a large or costly benchmark, record the selected IDs, why they cover the different paths, and the total size. On a representative task, also try an answer known to be wrong and check its expected score. Inspect the per-trial rewards and errors, including any benchmark-specific exceptions in the [adapter spec](adapters.mdx).

Keep the command, revisions, Harbor version, task IDs, expected and observed scores, terminal screenshot, and raw job logs together. Label a subset explicitly. Record an infrastructure error as unscored and investigate it before treating the task as an oracle failure.

## 4. Agree on parity scope, then have the author run it

After the first reviewer verifies the generated tasks, grading, and oracle results, the author and reviewer agree in the PR on task IDs or sampling seed, upstream and Harbor revisions, agent, model, tools, judge, repetitions, budget, and metric. If an upstream oracle is broken, document the affected IDs and agree with a maintainer on the scope before proceeding. Decide how to count failed attempts and retries. If a standard CLI agent is an extra Harbor-only check, report it separately from the matched comparison. The author runs that plan and links the raw submissions, logs, configs, and per-task grades at a pinned revision.

## 5. Check the scores and hand off to the second reviewer

Open the linked artifacts for both sides. Match task IDs and attempts to the agreed scope. Recompute each run's score from its task records, then the mean and sample SEM across runs. With one run, report the score and mark SEM unavailable. Compare the results with the README and `parity_experiment.json`. Give the second reviewer the upstream and Harbor numbers side by side for each reported cohort, with denominators and links. Investigate material differences using the [parity diagnostics](parity-diagnostics.md).

If only grading changed, inspect the saved submissions. Regrade them when they contain everything the new verifier needs. Agree on a new run for the affected scope if the agent saw a different task or essential state was lost.

The second reviewer checks the consequential findings against upstream, opens the oracle evidence, and verifies the parity numbers and their scope before signing off. Record the decision, revision, and remaining work in the tracker. If the author changes prompts, the environment, or scoring afterwards, revisit the affected checks before merge.
