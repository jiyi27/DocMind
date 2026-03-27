export function parseChatSources(sources = []) {
  return sources.map((source) => {
    const markdownMatch = source.match(/^\[(\d+)\]\s+\[(.+?)\]\((.+?)\)$/)
    if (markdownMatch) {
      return {
        index: markdownMatch[1],
        title: markdownMatch[2],
        url: markdownMatch[3],
      }
    }

    const plainMatch = source.match(/^\[(\d+)\]\s+(.+)$/)
    if (plainMatch) {
      return {
        index: plainMatch[1],
        title: plainMatch[2],
        url: '',
      }
    }

    return {
      index: '',
      title: source,
      url: '',
    }
  })
}
