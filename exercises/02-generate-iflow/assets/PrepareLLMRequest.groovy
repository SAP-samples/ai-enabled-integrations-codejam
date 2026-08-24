// This is Groovy Flowstep Version 2.x, running with Groovy runtime 4, Downgrade the script if older behaviour needed.

package script.v2

import com.sap.it.script.v2.api.Message;
import groovy.json.JsonOutput;

def Message processData(Message message) {

    def customerRequest = message.getProperty("customer_request")?.toString() ?: ""
    def trimmed = customerRequest.replaceAll(/[\r\n]+/, " ").trim()

    message.setProperty("trimmed_customer_request", trimmed)

    def payload = [
        config_ref: [
            scenario: message.getProperty("AICoreOrchestrationScenario")?.toString() ?: "",
            name: message.getProperty("AICoreOrchestrationName")?.toString() ?: "",
            version: message.getProperty("AICoreOrchestrationVersion")?.toString() ?: ""
        ],
        placeholder_values: [
            input: trimmed
        ]
    ]

    def jsonPayload = JsonOutput.toJson(payload)

    def messageLog = messageLogFactory.getMessageLog(message)
    if (messageLog != null) {
        messageLog.setStringProperty("Logging#LLMRequest", "LLMRequest")
        messageLog.addAttachmentAsString("LLMRequest", jsonPayload, "application/json")
    }

    message.setBody(jsonPayload)

    return message
}
