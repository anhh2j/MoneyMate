module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', ['feat', 'fix', 'perf', 'refactor', 'docs', 'test', 'build', 'ci', 'chore', 'style', 'revert']],
    'scope-enum': [2, 'always', ['capture', 'parser', 'dedup', 'categorizer', 'data', 'privacy', 'security', 'app', 'ci', 'build', 'docs', 'adr', 'deps', 'release']],
    'scope-empty': [2, 'never'],
    'subject-case': [0],
  },
};
