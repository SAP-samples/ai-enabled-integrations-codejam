# Troubleshooting

This page includes a list of common problems you might encounter while going through the exercises and their potential solutions.

## SAP Integration Suite

### iFlow deployment fails

**Symptom:** An iFlow fails to deploy with an error in the monitoring view.

**Solution:** Navigate to **Monitor > Integrations > All Artifacts** and click on the failed artifact to see the detailed error message. Common causes include:

- Missing or misconfigured credentials (check your Security Material entries)
- Missing external endpoint connectivity (check if the target system is reachable)

Here we can leverage the [**AI-assisted error resolution** feature](https://help.sap.com/docs/integration-suite/isuite-integrations-and-apis/ai-assisted-error-resolution?locale=en-US) in SAP Integration Suite. This feature uses AI to analyze the error and provide suggestions for resolving it.

![Trigger AI-assisted error resolution](assets/analyse-button.png)

## Customer Requests agent

### Cannot connect to model

**Symptom:** The agent shows an error when trying to send a message to the model, e.g. "Could not connect to the server".

**Solution:** Verify that the SAP AI Core connection details are configured properly in the environment.

### MCP tools are not called

**Symptom:** The agent is hallucinating data and not calling the MCP tools

**Solution:** 
Verify that the MCP URLs configured for the agent are correct.

## General - Cannot access the Altura Coffee Co. website

**Symptom:** The Altura Coffee Co. website URL provided by the instructor is not loading.

**Solution:** Check your network connection and verify the URL is correct. The URL will be shared by the instructor during the event. 🔐 If the site is slow to respond, try refreshing after a few seconds - it may be starting up.
