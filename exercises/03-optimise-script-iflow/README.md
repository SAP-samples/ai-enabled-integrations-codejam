# Exercise 03 - Optimise script in iFlow

In the previous exercise, we included a placeholder Groovy script in our iFlow. Now we will replace it with a meaningful script that enriches the payload, and then use the **Script Optimisation** feature in SAP Integration Suite to improve it. Script Optimisation is an AI-powered feature that analyses your Groovy code and suggests improvements for readability, performance, and correctness.

At the end of this exercise, you'll have an iFlow with an enhanced Groovy script, and you'll have seen how the Script Optimisation feature can help improve the quality of code written for integration flows.

## What the script will do

Our Groovy script will take the JSON response from the LLM (which we saw in Exercise 01) and enrich it with some additional metadata before the payload is sent to the customer service system. Specifically, the script will:

1. Parse the JSON response from the AI adapter
2. Count the number of address entries found in the `requests` array
3. Add a new field `address_count` to the JSON payload with this count
4. Set a message header with the urgency level extracted from the response

This is a simple but realistic transformation - adding derived data and setting headers based on payload content are very common tasks in integration scenarios.

## Write the initial script

👉 Open your iFlow from Exercise 02 and navigate to the Groovy script step. Replace the placeholder script with the following:

```groovy
import com.sap.gateway.ip.core.customdev.util.Message
import groovy.json.JsonSlurper
import groovy.json.JsonOutput

def Message processData(Message message) {
    def body = message.getBody(String.class)
    def json = new JsonSlurper().parseText(body)
    
    def addressCount = json.requests ? json.requests.size() : 0
    json.address_count = addressCount
    
    def urgency = json.urgency ?: "Unknown"
    message.setHeader("X-Urgency", urgency)
    
    message.setBody(JsonOutput.toJson(json))
    return message
}
```

👉 Save the script and redeploy the iFlow. Test it again with the sample request from Exercise 00 and verify that the response now includes the `address_count` field and that the `X-Urgency` header is set correctly.

> [!NOTE]
> The `address_count` field in the response is an example of the kind of simple enrichment that is useful for downstream consumers. For example, the customer service system could use this field to flag requests that mention multiple locations as potentially higher-effort cases.

## Use the Script Optimisation feature

Now that we have a working script, let's see how the Script Optimisation feature can help improve it.

👉 With the Groovy script open in the iFlow editor, look for the **Optimise Script** button or option (the exact label and location may vary depending on your SAP Integration Suite version).

👉 Trigger the script optimisation. The AI will analyse your script and suggest improvements. Review the suggestions carefully.

Some typical suggestions you might see include:

- Using `message.getBody(java.io.InputStream.class)` and reading with a buffered reader instead of directly calling `getBody(String.class)` for better memory efficiency with large payloads
- Adding null-safety checks
- Improving variable naming
- Extracting repeated logic into helper methods

> [!TIP]
> 🧭 Script Optimisation suggestions are not always applicable to every scenario. It is important to understand *why* a suggestion is being made before applying it. Some suggestions improve performance at scale but are not meaningful for small payloads like the ones in this CodeJam.

👉 Apply the suggestions that make sense for our scenario and verify that the iFlow still functions correctly after the changes.

> [!IMPORTANT]
> After applying any script changes, always redeploy and re-test the iFlow. An optimisation that looks correct syntactically can still change the behaviour of the script in subtle ways.

## Verify the end-to-end flow

👉 Send a final test request via the [website](${credentialsObj.alturawebsite.url}):

```text
The espresso machine in our Barcelona office (Avinguda Diagonal, 201, 08018) is 
making a grinding noise and the coffee is coming out cold. Please send a 
technician as soon as possible.

Regards,
${userDetails.firstName} ${userDetails.lastName}
```

👉 Check the monitoring view to confirm the message was processed without errors.

👉 Check the customer service system to confirm the new request has been created.

## Summary

We now have an iFlow with a meaningful Groovy script that enriches the LLM response with additional metadata. We also explored the Script Optimisation feature and applied relevant improvements to our code. This combination of AI-generated structure and AI-assisted code improvement is a good example of how AI features in SAP Integration Suite can accelerate development.

In the next exercise, we will shift focus to MCP and explore how the customer service system exposes an MCP server before diving on the MCP Gateway functionality.

## Further Study

* [Script Optimisation in SAP Cloud Integration](https://help.sap.com/docs/integration-suite/sap-integration-suite/optimise-script)
* [Groovy scripting reference for Cloud Integration](https://help.sap.com/docs/integration-suite/sap-integration-suite/groovy-api)
* [Message processing log in Cloud Integration](https://help.sap.com/docs/integration-suite/sap-integration-suite/message-processing-log)

---

If you finish earlier than your fellow participants, you might like to ponder these questions. There isn't always a single correct answer and there are no prizes - they're just to give you something else to think about.

1. The script we wrote counts the number of addresses in the `requests` array. Can you think of other useful derived fields we could compute from the LLM response and add to the payload?
2. We set the urgency level as a message header (`X-Urgency`). What are the trade-offs of passing data as headers vs. keeping everything in the message body?
3. The Script Optimisation feature uses an LLM to suggest improvements. Can you think of cases where following the LLM's suggestions could actually make the code worse?
   <details>
    <summary>⇟ Hint 🔦</summary>
    <i>Consider suggestions that are generically correct for large-scale production systems but introduce unnecessary complexity for simple, short-lived integration scripts. Also think about cases where the LLM might not understand the specific constraints of the Cloud Integration runtime environment.</i>
   </details>

## Next

Continue to 👉 [Exercise 04 - Customer Service system API as MCP server](../04-customer-service-api-mcp-server/README.md)
