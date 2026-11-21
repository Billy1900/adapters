# Reviewing an adapter PR

The first reviewer follows a task from upstream through generation and grading. The author runs the agreed parity experiment. The second reviewer decides whether the evidence supports merging the final revision. Both reviewers read the user-facing text, including the task instructions, adapter README, parity notes, and linked reproduction instructions.

Track each incoming PR, including WIPs, in the review tracker. Record the PR, benchmark, stage, first and second reviewers, reviewed commit, evidence links, and who owns the next action. Update the row when the PR changes hands.

## 1. Run the bot and read its comments

Trigger `/review-adapter`. Read the report and coverage table, including which revision and files the bot checked. Follow each finding back to the code. Check the author's fix or explain in the thread why the finding does not apply.

If structural validation stops the bot before code review, leave a short comment naming the missing files or formatting errors. Ask the author to fix them, then rerun the bot so it can finish the code review. Normally, move on once structural validation passes and every finding has been addressed. On a tight timeline, you can start the upstream comparison in step 2 while the author makes those fixes. If only the parity results are missing, go ahead with steps 2 and 3 while the author prepares the experiment.

## 2. Compare the adapter with upstream

Use the upstream commit pinned by the author. For each distinct way the adapter generates a task, runs an agent, or grades a submission, follow a concrete task through that path on both sides.

- **Task setup.** Start with an upstream task ID. Does it map to the right split, prompt, input files, and starting state? Compare the tools, turn or time limits, and what the agent has to submit. Can it do the same work with the same information? Check that reference answers and grading inputs stay private where upstream keeps them private.
- **Environment.** Inspect the generated task and its startup code. Are the files, dependencies, and services available where the agent expects them? If the adapter simulates a service, follow one interaction the task depends on. For example, if upstream asks the agent to retry a failed request, does the simulated service return the same error and enforce the same wait?
- **Verifier.** Follow the agent's submission into the grading program. Compare the criteria, weights, partial credit, and failure handling with the upstream rubric. Where upstream distinguishes a wrong answer from a judge or service outage, check both cases. Can you tell from the trial record whether the answer earned zero or grading never finished?
- **Separate verifier.** Expect new tasks to use a separate verifier on the [latest stable Harbor release](https://github.com/harbor-framework/harbor/releases/latest). Check which files and state actually reach the grader. If scoring depends on live state, ask how the adapter preserves it and agree on any exception with a maintainer.
- **Readability.** Read the instructions and README as someone running the adapter for the first time. Can you find the command to run, the dataset revision and changes from upstream, and which tasks, agents, and judges each result covers? For example, if the oracle ran on a subset, can you tell from the results table how many tasks it covered out of the full dataset?

An agent can help you locate upstream code, explain an implementation, summarize a diff, or trace an artifact back to its source. Open the relevant files yourself, check what the adapter does, and write the finding in your own words. Give the author a task ID or a small example, explain what upstream does in that case, and say what result would show the fix worked.

## 3. Generate tasks and run the oracle

Check out the adapter commit under review. Use the author's documented command to generate tasks into an empty directory, preferably on your own machine. Compare task IDs and file contents with a pinned commit of the dataset PR. Look for missing, extra, and changed files. If the author generated the uploaded dataset with an older adapter commit, check where that commit is documented and whether the changes since then explain the diff. If today's generator produces the correct tasks and the upload is out of date, ask the author to regenerate it. If generating from the reviewed commit still produces incorrect behavior, fix the adapter first.

Run the reference solution on the newly generated tasks using the latest stable release of the Harbor CLI. Run every task in datasets with fewer than 50 tasks. For larger datasets, choose a subset if a full run is costly. Record the total size, the selected task IDs, and why they cover the different paths. Also try a known wrong answer on a representative task and check that it receives the score the rubric assigns it.

Inspect each trial's reward and errors against its expected score, including any benchmark-specific [oracle exceptions](adapters.mdx#broken-oracles-in-the-original-benchmark). Record the command, revisions, Harbor version, task IDs, expected and observed scores, terminal screenshot, and raw job logs. Label any subset. Investigate unscored trials separately from graded answers that fell short.

## 4. Agree on scope, then have the author run parity

If an oracle falls short, record the affected task IDs, what you expected, and what happened. Fix what the adapter can fix and rerun those tasks. If a reference solution is already broken upstream or an external limitation remains, discuss it with a maintainer. Agree on which tasks the adapter supports, which will be included in parity, and how the README will explain any exclusions.

Before the author runs parity, agree in the PR on the task IDs or sampling seed, upstream and Harbor revisions, agent, model, prompts, tools, judge, repetitions, budget, and metric. Apply the same settings on both sides. If failed attempts or retries come up during the run, agree with the author on how to count them, keep the original attempts, and use the same rule on both sides. If the author also tries a CLI agent such as Codex only on Harbor, give that result its own row. A comparison with upstream needs a run of the same agent there.

After the run, the author links the evidence in the adapter PR.

- **Hugging Face.** Upload the run config, upstream and Harbor run outputs, oracle outputs, and per-run result JSONs in the [documented directory layout](adapters.mdx#step-7-upload-parity-results). Keep the original submissions, agent execution logs, and per-task grades so a reviewer can follow one result end to end. Open or update a dataset PR on [harborframework/parity-experiments](https://huggingface.co/datasets/harborframework/parity-experiments). If the full logs or submissions live in the author's fork, include a link to that exact revision in the dataset PR.
- **Adapter PR.** Under `src/<adapter-name>/`, record benchmark and coverage metadata in `adapter_metadata.json`. Put experiment settings, raw run scores, metrics, and the Hugging Face PR URL (`parity_pr`) in `parity_experiment.json`. Summarize both sides in the README table and link the dataset and parity PRs. See the [results schema](adapters.mdx#step-6-record-parity-results).

## 5. Verify the reported scores

Open the artifacts for both sides and match task IDs, attempts, and denominators to the agreed scope. Verify the README and JSON numbers against the raw run scores. Check the mean, sample standard error (SEM), and whether the two run-score ranges overlap. You can use an agent to recompute a run's score from its individual task records, especially if a total or denominator looks wrong. Investigate material gaps using the [parity diagnostics](parity-diagnostics.md).

Matched parity requires at least two runs per side, preferably three or more. If only one run is available, for example from an upstream paper or a pilot, label it with its score and “SEM unavailable.” Ask for the remaining runs before signing off on parity.

If the author changes the verifier after parity has run, first check whether the agent saw the same task and whether the saved submissions contain everything the updated verifier needs. If both hold and only grading changed, regrade those submissions and update the results. If the prompt, tools, or agent-visible environment changed, or a required piece of state was lost, rerun the affected tasks with the agent.

## 6. Second reviewer decides whether to merge

Start with the current PR commit and the first reviewer's handoff. Check anything that changed since the recorded runs. Before approving, answer these questions yourself:

- **Does the adapter do what upstream asks?** Pick a representative task and compare its setup and grading with upstream. Revisit any discrepancy the first reviewer flagged and check the fix or agreed scope. Confirm that structural validation passed and each bot and human finding has been addressed.
- **What did the oracle establish?** Open the trial records for a reference answer and a known wrong answer. Compare expected and observed scores. Check the dataset revision, the number of tasks run, and the IDs and explanations for any exceptions.
- **Do the parity numbers support this scope?** Open the linked artifacts and compare the upstream and Harbor scores side by side for each reported group. Check the agent and judge, task counts, repetitions, and treatment of retries. Confirm that the results apply to the revision being merged.
- **Can a new reader use this PR?** Read the task instructions, README, parity table, and linked run instructions yourself. Can you find the command to reproduce a result and tell which tasks and settings it covers? Ask for an edit if the reader has to piece that together from the review thread.

Approve when the evidence supports the documented scope. If a fix, run, or clarification is still needed, leave a short comment naming it and who should follow up. Record the decision and commit in the tracker. If a later commit changes a prompt, environment, or grading rule, revisit the affected checks before merge.
