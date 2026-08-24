function escape(htmlStr) {
  return htmlStr
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function parseCredential(full, first, second, third, creds) {
  console.log("Replacing: " + full + " | " + third);
  try {
    if (third) {
      if (first in creds && third in creds[first]) {
        return escape(creds[first][third]);
      } else {
        console.log("Credential not found for " + first + " and " + third);
        return full;
      }
    } else {
      try {
        if (first in creds) {
          return creds[first];
        } else {
          console.log("Credential not found for " + first);
          return full;
        }
      } catch (e) {
        console.log("Error parsing credential for " + first + ": " + full);
        return full;
      }
    }
  } catch (e) {
    return full;
  }
}

function getDynamicValueByPath(dynamic_value, path, index, obj) {
  console.log("Dynamic value: " + dynamic_value);

  const keys = path.split(".");
  let value = obj;

  for (const key of keys) {
    if (value && typeof value === "object" && key in value) {
      value = value[key];
    } else {
      // Dynamic value not found, return original string
      return dynamic_value;
    }
  }

  return value;
}
