# Prerequisites

There are hardware, software, and service prerequisites for participating in this CodeJam. The exercises will be developed using SAP Integration Suite and SAP AI Core, which will be made available for the CodeJam.

## Accessing the supporting material referenced in exercises

In this CodeJam, you will see that across exercises, there are references to files that will help you get started or that are needed to complete the activities. To access these files, you can download the individual files directly from the repository website, or you can make a copy of the repository on your local machine by following one of the options below:

1. **(Recommended)** Clone the git repository in your local machine with the following command:

   ```bash
   git clone https://github.com/SAP-samples/ai-enabled-integrations-codejam.git
   ```

   > If you've set up [SSH to communicate with GitHub](https://docs.github.com/en/authentication/connecting-to-github-with-ssh) from your local machine, you can clone it using the following command: `git clone git@github.com:SAP-samples/ai-enabled-integrations-codejam.git`

   Using `git` is recommended as there might be future updates on the CodeJam content; updating your local copy will just be a command away.

   ```bash
   git pull origin main
   ```

2. Alternatively, download the [repository as a zip](https://github.com/SAP-samples/ai-enabled-integrations-codejam/archive/refs/heads/main.zip), and unzip it.

## Hardware

None.

## Software

### Web browser

A web browser supported by SAP Integration Suite[^1]: For the UIs of the service, the following browsers are supported on Microsoft Windows PCs and, where mentioned below, on macOS. Note that, however, certain limitations might apply for specific browsers:

```text
SAP Integration Suite has been tested using the following browsers:
- Google Chrome (latest version)
- Microsoft Edge (latest version)
- Mozilla Firefox (latest version)
```

### Docker

[Docker Desktop](https://www.docker.com/products/docker-desktop/) (or equivalent container runtime) is required for Exercise 06, where you will run Open WebUI locally. Make sure Docker is installed and running before attending the event.

### curl or Bruno (REST client)

Some exercises require calling REST APIs. You can use any HTTP client you are comfortable with:
- [Bruno](https://www.usebruno.com/) - a Git-friendly open source API client (recommended)
- [curl](https://curl.se/) - available on most operating systems

## Services

### SAP Integration Suite

Access to an SAP Integration Suite tenant is required. As part of this CodeJam, your instructor will provide the necessary credentials to access a shared tenant. The tenant will have the following capabilities enabled:

- **Cloud Integration** - for building and running integration flows
- **API Management** - for managing APIs and configuring the MCP Gateway
- **Integration Advisor** - available but not used directly in the exercises

If you are completing this CodeJam on your own, you can use an [SAP BTP Trial account](https://www.sap.com/products/technology-platform/trial.html) and set up SAP Integration Suite there.

### SAP AI Core

SAP AI Core provides the LLM capabilities used in this CodeJam. An instance of SAP AI Core will be pre-configured in the shared SAP Integration Suite tenant. It will have the following already set up:

- A deployed model (e.g. `gpt-4o-mini` or equivalent)
- A prompt template for processing customer support requests

If running on your own, refer to the [SAP AI Core documentation](https://help.sap.com/docs/sap-ai-core) for setup instructions.

### Open WebUI

[Open WebUI](https://github.com/open-webui/open-webui) is an open source, self-hosted web interface for interacting with LLMs. It will be used in Exercise 06 to configure an LLM client that connects to SAP AI Core via a proxy and uses MCP tools exposed through SAP API Management.

Open WebUI doesn't support SAP AI Core out of the box. An SAP AI Core proxy will be made available for participants to configure as part of the workshop. 🔐

You can run Open WebUI locally using Docker:

```bash
docker run -d -p 3000:8080 --name open-webui ghcr.io/open-webui/open-webui:main
```

Once running, Open WebUI will be accessible at [http://localhost:3000](http://localhost:3000).

> [!NOTE]
> Make sure to pull the Open WebUI image before the event to avoid downloading it during the CodeJam.

## Checklist

Use the checklist below to verify that you have everything ready before the CodeJam:

- [ ] Access to a web browser (Chrome, Edge, or Firefox - latest version)
- [ ] Docker Desktop installed and running
- [ ] Bruno or curl available for REST API calls
- [ ] SAP Integration Suite credentials received from instructor 🔐
- [ ] SAP AI Core proxy URL and credentials received from instructor 🔐
- [ ] Open WebUI Docker image pulled (`docker pull ghcr.io/open-webui/open-webui:main`)

[^1]: [Browser support for SAP Integration Suite](https://help.sap.com/docs/integration-suite/sap-integration-suite/browser-support)
