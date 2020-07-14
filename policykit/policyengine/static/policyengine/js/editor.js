var name = '{{ field.field.name }}'
if(['filter', 'initialize', 'check', 'notify', 'success', 'fail'].indexOf(name) >= 0) {
  var textArea = document.getElementById('id_{{ field.field.name }}');
  var editor = CodeMirror.fromTextArea(textArea, {
      mode: 'python',
      autoRefresh: true,
      lineNumbers: true,
      theme: 'eclipse'
  });
  editor.setValue(textArea.value);

  // https://stackoverflow.com/questions/11401317/autocomplete-for-python-in-codemirror
  editor.on('inputRead', function onChange(editor, input) {
      if (input.text[0] === ';' || input.text[0] === ' ' || input.text[0] === ":") {
          return;
      }
      editor.showHint({
          hint: CodeMirror.pythonHint
      });
  });
}
