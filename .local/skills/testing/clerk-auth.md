---
name: clerk-auth-testing
description: Programmatic login for testing applications that use Clerk Auth.
---

# How does Testing Skill Interact with Clerk Auth

Clerk Auth supports testing arbitrary users programmatically. Make sure you mention in the testing task that you are testing a Clerk Auth application and make it abundantly explict that login claims need to be overridden.

During testing, the testing agent can sign in users without interacting with Clerk's UI — the sign-in is fully programmatic. This means test plans should describe *who* to sign in as (name, email) and what to verify after login, but should not include steps that interact with Clerk's sign-in/sign-up UI components.

## Example Test Plan

<test_plan>
[New Context] Create a new browser context
...
n. [Clerk Auth] Sign in as {firstName: "Normal", lastName: "Person", email: `user${nanoid(6)}@example.com`}. Note the email for future use (say ${login_email}).
n+1. [Browser] Verify the app shows the logged-in state (e.g. redirected to dashboard/home).
n+2. [Verify] Verify the user name is "Normal Person" (data-testid="user-name-display")
n+3. [Verify] Verify the user email is ${login_email} (data-testid="user-email-display")
</test_plan>

Customize this to the application at hand.
