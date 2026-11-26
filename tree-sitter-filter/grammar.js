export default grammar({
  name: 'filter',
  extras: $ => [/\s/],
  rules: {
    query: $ => $.comparison,
    comparison: $ => seq($.identifier, choice('=', '!=', '>', '<', '>=', '<='), $.number),
    number: $ => /\d+(\.\d+)?/,
    identifier: $ => /[a-zA-Z_][a-zA-Z0-9_.]*/,
  }
});