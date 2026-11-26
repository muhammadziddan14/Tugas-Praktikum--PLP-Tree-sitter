export default grammar({
  name: 'filter',
  extras: $ => [/\s/],
  word: $ => $.identifier,
  rules: {
    query: $ => $._expr,
    _expr: $ => choice($.comparison, $.and_expression, $.or_expression),
    comparison: $ => seq($.identifier, choice('=', '!=', '>', '<', '>=', '<='), $._value),
    and_expression: $ => prec.left(2, seq($._expr, 'and', $._expr)),
    or_expression: $ => prec.left(1, seq($._expr, 'or', $._expr)),
    _value: $ => choice($.string, $.number, $.boolean),
    string: $ => /"[^"]*"/,
    number: $ => /\d+(\.\d+)?/,
    boolean: $ => choice('true', 'false'),
    identifier: $ => /[a-zA-Z_][a-zA-Z0-9_.]*/,
  }
});