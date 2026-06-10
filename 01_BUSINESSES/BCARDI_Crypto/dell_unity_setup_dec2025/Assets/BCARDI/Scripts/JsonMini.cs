using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace BCARDI
{
    // Minimal JSON parser to avoid external dependencies.
    public static class JsonMini
    {
        public static object Deserialize(string json)
        {
            if (string.IsNullOrEmpty(json))
            {
                return null;
            }
            return new Parser(json).ParseValue();
        }

        private sealed class Parser
        {
            private readonly string _json;
            private int _index;

            public Parser(string json)
            {
                _json = json;
            }

            public object ParseValue()
            {
                SkipWhitespace();
                if (_index >= _json.Length)
                {
                    return null;
                }

                char c = _json[_index];
                if (c == '{') return ParseObject();
                if (c == '[') return ParseArray();
                if (c == '"') return ParseString();
                if (c == '-' || char.IsDigit(c)) return ParseNumber();
                if (Match("true")) return true;
                if (Match("false")) return false;
                if (Match("null")) return null;

                return null;
            }

            private Dictionary<string, object> ParseObject()
            {
                var dict = new Dictionary<string, object>();
                _index++; // '{'
                SkipWhitespace();
                if (Peek('}')) { _index++; return dict; }

                while (_index < _json.Length)
                {
                    SkipWhitespace();
                    string key = ParseString();
                    SkipWhitespace();
                    Expect(':');
                    SkipWhitespace();
                    object value = ParseValue();
                    dict[key] = value;
                    SkipWhitespace();
                    if (Peek('}')) { _index++; break; }
                    Expect(',');
                }
                return dict;
            }

            private List<object> ParseArray()
            {
                var list = new List<object>();
                _index++; // '['
                SkipWhitespace();
                if (Peek(']')) { _index++; return list; }

                while (_index < _json.Length)
                {
                    SkipWhitespace();
                    list.Add(ParseValue());
                    SkipWhitespace();
                    if (Peek(']')) { _index++; break; }
                    Expect(',');
                }
                return list;
            }

            private string ParseString()
            {
                Expect('"');
                var sb = new StringBuilder();
                while (_index < _json.Length)
                {
                    char c = _json[_index++];
                    if (c == '"') break;
                    if (c == '\\')
                    {
                        if (_index >= _json.Length) break;
                        char esc = _json[_index++];
                        switch (esc)
                        {
                            case '"': sb.Append('"'); break;
                            case '\\': sb.Append('\\'); break;
                            case '/': sb.Append('/'); break;
                            case 'b': sb.Append('\b'); break;
                            case 'f': sb.Append('\f'); break;
                            case 'n': sb.Append('\n'); break;
                            case 'r': sb.Append('\r'); break;
                            case 't': sb.Append('\t'); break;
                            case 'u':
                                sb.Append(ParseUnicode());
                                break;
                            default:
                                sb.Append(esc);
                                break;
                        }
                    }
                    else
                    {
                        sb.Append(c);
                    }
                }
                return sb.ToString();
            }

            private char ParseUnicode()
            {
                if (_index + 4 > _json.Length) return '?';
                string hex = _json.Substring(_index, 4);
                _index += 4;
                if (ushort.TryParse(hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out ushort code))
                {
                    return (char)code;
                }
                return '?';
            }

            private object ParseNumber()
            {
                int start = _index;
                if (_json[_index] == '-') _index++;
                while (_index < _json.Length && char.IsDigit(_json[_index])) _index++;
                if (_index < _json.Length && _json[_index] == '.')
                {
                    _index++;
                    while (_index < _json.Length && char.IsDigit(_json[_index])) _index++;
                    string f = _json.Substring(start, _index - start);
                    if (double.TryParse(f, NumberStyles.Float, CultureInfo.InvariantCulture, out double fd))
                    {
                        return fd;
                    }
                }
                string i = _json.Substring(start, _index - start);
                if (long.TryParse(i, NumberStyles.Integer, CultureInfo.InvariantCulture, out long ld))
                {
                    if (ld >= int.MinValue && ld <= int.MaxValue) return (int)ld;
                    return ld;
                }
                return 0;
            }

            private void SkipWhitespace()
            {
                while (_index < _json.Length && char.IsWhiteSpace(_json[_index])) _index++;
            }

            private bool Peek(char c)
            {
                return _index < _json.Length && _json[_index] == c;
            }

            private void Expect(char c)
            {
                if (_index >= _json.Length || _json[_index] != c)
                {
                    throw new FormatException("Unexpected JSON token");
                }
                _index++;
            }

            private bool Match(string token)
            {
                if (_index + token.Length > _json.Length) return false;
                if (string.Compare(_json, _index, token, 0, token.Length, StringComparison.Ordinal) == 0)
                {
                    _index += token.Length;
                    return true;
                }
                return false;
            }
        }
    }
}
