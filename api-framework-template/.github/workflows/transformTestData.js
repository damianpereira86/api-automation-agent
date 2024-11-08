import fs from "fs";

const originalData = JSON.parse(fs.readFileSync("testStructure.json", "utf8"));
const testsByFile = {};

for (const test of originalData.tests) {
  if (!testsByFile[test.file]) {
    testsByFile[test.file] = [];
  }
  testsByFile[test.file].push({
    suite: test.fullTitle.replace(test.title, "").trim(),
    title: test.title,
  });
}

const testsBySuite = {};

for (const [filePath, tests] of Object.entries(testsByFile)) {
  for (const test of tests) {
    if (!testsBySuite[test.suite]) {
      testsBySuite[test.suite] = [];
    }
    testsBySuite[test.suite].push(test.title);
  }
}

const newTestData = {
  testsBySuite,
};

fs.writeFileSync("groupedTestStructure.json", JSON.stringify(newTestData, null, 2));
