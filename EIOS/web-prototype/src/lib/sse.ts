/** Incremental Server-Sent Events parser: feed it text chunks, it calls back once per complete event. */
export function createSseParser(onEvent: (eventName: string, data: string) => void): (chunk: string) => void {
  let buffer = '';
  let eventName = 'message';
  let dataLines: string[] = [];

  const dispatch = () => {
    if (dataLines.length > 0) onEvent(eventName, dataLines.join('\n'));
    eventName = 'message';
    dataLines = [];
  };

  return (chunk: string) => {
    buffer += chunk;
    let newline = buffer.search(/\r\n|\n|\r/);
    while (newline !== -1) {
      const terminator = buffer.startsWith('\r\n', newline) ? 2 : 1;
      const line = buffer.slice(0, newline);
      buffer = buffer.slice(newline + terminator);
      if (line === '') dispatch();
      else if (!line.startsWith(':')) {
        const colon = line.indexOf(':');
        const field = colon === -1 ? line : line.slice(0, colon);
        const value = colon === -1 ? '' : line.slice(colon + 1).replace(/^ /, '');
        if (field === 'event') eventName = value;
        else if (field === 'data') dataLines.push(value);
      }
      newline = buffer.search(/\r\n|\n|\r/);
    }
  };
}
