## Description
### Change summary
<!-- Add breif description of what has changed and why-->

### Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Code refactor

### Impacts
- **Does this impact any dependent apps, tools or scripts?**
<!--  Yes, this impacts...  -->

- **Does this change an existing contract and how you are handling the change?**
<!-- e.g. changing an API to raise an exception instead of returning None or a default value -->
<!-- Yes, this changes a function used in /v1/xxx/ ...  -->

- **Are there any risks with this deployment and how you are mitigating them?**
<!-- Yes, the risk is ... -->

### Related links
- [Jira](<Replace with Jira link>)
- [Design doc](<Replace with design doc link>)

## How Has This Been Tested?
Please describe the tests that you ran to verify your changes. 
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests

## Checklist:
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit/integration tests pass locally with my changes
- [ ] There are no flake8 or mypy issues with my changes

## Rollout Plan
<!-- Check one or more that apply -->
- [ ] Feature flag
- [ ] Experiment
- [ ] Fallback, in case of failures
- [ ] Timing (deploy during off-peak hours)

## Post-deployment Validation Plan
- **How are you planning to validate this in production and follow up on the rollout?**
<!-- I will turn on the feat flag and monitor ... -->
- **Link to metrics that you will need to validate**
   - [WaveFront](<link>)
   - [Splunk](<link>)
   - [NewRelic](<link>)
   - [Sentry](<link>)

## Required reviewers
@tag relevant teams here for review
