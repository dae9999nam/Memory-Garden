export function buildStoryPrompt ({ date, place, weather, notes }) {
  const details = [
    date ? `Date: ${date}` : null,
    place ? `Place: ${place}` : null,
    weather ? `Weather: ${weather}` : null,
    notes ? `Additional context: ${notes}` : null
  ].filter(Boolean).join('\n');

  return `You are a warm and imaginative storyteller. Use the provided photos and contextual details to craft a cohesive, multi-paragraph narrative that captures the mood of the moment.\n\nContext:\n${details}\n\nDescribe the people, setting, and emotions you infer from the images, weaving them into an evocative short story written in the past tense. End with a reflective closing line.`;
}
