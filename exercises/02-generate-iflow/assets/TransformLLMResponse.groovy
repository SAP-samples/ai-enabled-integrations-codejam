// This is Groovy Flowstep Version 2.x, running with Groovy runtime 4, Downgrade the script if older behaviour needed.

/* Refer the link below to learn more about the use cases of script.
https://help.sap.com/viewer/368c481cd6954bdfa5d0435479fd4eaf/Cloud/en-IN/148851bf8192412cba1f9d2c17f4bd25.html

If you want to know more about the SCRIPT APIs, refer the link below
https://help.sap.com/doc/a56f52e1a58e4e2bac7f7adbf45b2e26/Cloud/en-IN/index.html */

package script.v2;

import groovy.json.JsonSlurper;
import groovy.json.JsonOutput;
import com.sap.it.script.v2.api.Message;

def Map mergeMaps(Map base, Map overrides) {
    def result = [:] + base
    overrides.each { k, v ->
        result[k] = (result[k] instanceof Map && v instanceof Map) ? mergeMaps(result[k] as Map, v as Map) : v
    }
    return result
}

def String extractJsonFromMarkdown(String content) {
    // Strip ```json ... ``` fences if present
    def matcher = content =~ /(?s)```(?:json)?\s*([\s\S]*?)```/
    if (matcher.find()) {
        return matcher.group(1).trim()
    }
    return content.trim()
}

def Message processData(Message message) {

    def jsonSlurper = new JsonSlurper();

    // Parse LLM response from message body
    def llmResponseBody = message.getBody(String)
    def llmJson = llmResponseBody ? jsonSlurper.parseText(llmResponseBody) : [:]

    // Extract embedded JSON from final_result.choices[0].message.content
    def rawContent = llmJson?.final_result?.choices?.get(0)?.message?.content
    if (!rawContent) {
        throw new RuntimeException("Cannot find final_result.choices[0].message.content in LLM response")
    }
    def extractedJsonStr = extractJsonFromMarkdown(rawContent as String)
    def llmExtractedJson = jsonSlurper.parseText(extractedJsonStr)

    // Parse originalBody property and extract its data field
    def originalBody = message.getProperty("originalBody")
    def originalJson = originalBody ? jsonSlurper.parseText(originalBody instanceof String ? originalBody : originalBody.toString()) : [:]
    def dataJson = originalJson?.data instanceof Map ? originalJson.data : [:]

    // Merge: LLM extracted JSON overrides data field values
    def mergedJson = mergeMaps(dataJson as Map, llmExtractedJson as Map)

    // Remove customer_request field if present as the service expects the value in request_original
    mergedJson.remove("customer_request")

    def mergedPayload = JsonOutput.prettyPrint(JsonOutput.toJson(mergedJson))

    def messageLog = messageLogFactory.getMessageLog(message)
    if (messageLog != null) {
        messageLog.setStringProperty("Logging#MergedPayload", "Merged Payload")
        messageLog.addAttachmentAsString("MergedPayload", mergedPayload, "application/json")
    }

    message.setBody(mergedPayload)

    return message
}
