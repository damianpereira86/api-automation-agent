import fs from "fs";
import axios from "axios";

const userRequirement = process.env.USER_REQUIREMENT;
const tests = JSON.parse(fs.readFileSync("groupedTestStructure.json", "utf8"));

const payload = {
  tests: tests,
  requirement: userRequirement,
};

const apiEndpoint = "https://openai-api-proxy-dev-rtu664353a-uc.a.run.app/api/get-regex-for-run";

const response = await axios.post(apiEndpoint, payload, {
  headers: {
    "Content-Type": "application/json",
  },
});

const responseData = response.data;

console.log(responseData);
const regexPattern = /^Regex: (.*)$/;
const match = responseData.match(regexPattern);
const extractedValue = match ? match[1] : null;
if (extractedValue !== null) {
  fs.appendFileSync(process.env.GITHUB_ENV, `REGEX=${extractedValue}\n`);
}
