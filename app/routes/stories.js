import express from 'express';
import { Readable } from 'node:stream';
import { getDb, getBucket, toObjectId } from '../db/mongo.js';
import { uploadImages } from '../middleware/uploads.js';
import { buildStoryPrompt } from '../utils/prompt.js';
import { generateStoryFromImages } from '../services/ollama.js';

const router = express.Router();
const STORIES_COLLECTION = 'stories';

function bufferToStream (buffer) {
  const readable = new Readable();
  readable.push(buffer);
  readable.push(null);
  return readable;
}

async function storeImages (files) {
  const bucket = getBucket();
  const photos = [];

  for (const file of files) {
    const uploadStream = bucket.openUploadStream(file.originalname, {
      contentType: file.mimetype,
      metadata: {
        size: file.size
      }
    });

    await new Promise((resolve, reject) => {
      bufferToStream(file.buffer)
        .pipe(uploadStream)
        .on('error', reject)
        .on('finish', (gridFile) => {
          photos.push({
            id: gridFile._id,
            filename: gridFile.filename,
            contentType: gridFile.contentType,
            length: gridFile.length,
            uploadDate: gridFile.uploadDate
          });
          resolve();
        });
    });
  }

  return photos;
}

async function deleteImages (photos) {
  if (!photos || photos.length === 0) {
    return;
  }
  const bucket = getBucket();
  for (const photo of photos) {
    if (!photo?.id) continue;
    try {
      await bucket.delete(toObjectId(photo.id));
    } catch (error) {
      // Ignore missing files and continue deleting the rest.
      if (error.code !== 26 && error.code !== 'ENOENT') {
        throw error;
      }
    }
  }
}

function parseStoryContext (body, { includeUndefined = false } = {}) {
  const parseField = (key) => {
    if (!(key in body)) {
      return includeUndefined ? undefined : null;
    }
    const value = body[key];
    if (typeof value !== 'string') {
      return value ?? null;
    }
    const trimmed = value.trim();
    return trimmed === '' ? null : trimmed;
  };

  return {
    date: parseField('date'),
    place: parseField('place'),
    weather: parseField('weather'),
    notes: parseField('notes')
  };
}

function ensureRequiredContext (context) {
  const missing = ['date', 'place', 'weather'].filter((key) => !context[key]);
  if (missing.length) {
    const error = new Error(`Missing required fields: ${missing.join(', ')}`);
    error.status = 400;
    throw error;
  }
}

function serializeStory (story, req) {
  if (!story) return null;

  const baseUrl = `${req.protocol}://${req.get('host')}`;
  const photos = (story.photos || []).map((photo) => ({
    ...photo,
    id: photo.id.toString(),
    downloadUrl: `${baseUrl}/stories/${story._id.toString()}/photos/${photo.id.toString()}`
  }));

  return {
    id: story._id.toString(),
    prompt: story.prompt,
    context: story.context,
    story: story.story,
    photos,
    createdAt: story.createdAt,
    updatedAt: story.updatedAt
  };
}

router.post('/', uploadImages, async (req, res, next) => {
  try {
    const files = req.files || [];
    if (!files.length) {
      const error = new Error('At least one photo is required.');
      error.status = 400;
      throw error;
    }

    const context = parseStoryContext(req.body);
    ensureRequiredContext(context);

    let photos = [];
    try {
      photos = await storeImages(files);
      const prompt = buildStoryPrompt(context);
      const base64Images = files.map((file) => file.buffer.toString('base64'));
      const storyText = await generateStoryFromImages({ prompt, images: base64Images });

      const now = new Date();
      const doc = {
        prompt,
        context,
        story: storyText,
        photos,
        createdAt: now,
        updatedAt: now
      };

      const db = getDb();
      const result = await db.collection(STORIES_COLLECTION).insertOne(doc);

      photos = null;
      res.status(201).json(serializeStory({ ...doc, _id: result.insertedId }, req));
    } catch (innerError) {
      if (photos?.length) {
        try {
          await deleteImages(photos);
        } catch (cleanupError) {
          console.error('Failed to clean up uploaded photos after error', cleanupError);
        }
      }
      throw innerError;
    }
  } catch (error) {
    next(error);
  }
});

router.put('/:storyId/photos', uploadImages, async (req, res, next) => {
  try {
    const storyId = toObjectId(req.params.storyId);
    const files = req.files || [];

    if (!files.length) {
      const error = new Error('Updated photos are required.');
      error.status = 400;
      throw error;
    }

    const db = getDb();
    const stories = db.collection(STORIES_COLLECTION);
    const story = await stories.findOne({ _id: storyId });
    if (!story) {
      const error = new Error('Story not found.');
      error.status = 404;
      throw error;
    }

    const contextUpdates = parseStoryContext(req.body, { includeUndefined: true });
    const context = { ...story.context };
    for (const [key, value] of Object.entries(contextUpdates)) {
      if (value !== undefined) {
        context[key] = value;
      }
    }
    ensureRequiredContext(context);

    let newPhotos = [];
    try {
      newPhotos = await storeImages(files);
      const base64Images = files.map((file) => file.buffer.toString('base64'));
      const prompt = buildStoryPrompt(context);
      const storyText = await generateStoryFromImages({ prompt, images: base64Images });

      await deleteImages(story.photos);

      const update = {
        $set: {
          context,
          prompt,
          story: storyText,
          photos: newPhotos,
          updatedAt: new Date()
        }
      };

      await stories.updateOne({ _id: storyId }, update);
      const updated = await stories.findOne({ _id: storyId });
      newPhotos = null;
      res.json(serializeStory(updated, req));
    } catch (innerError) {
      if (newPhotos?.length) {
        try {
          await deleteImages(newPhotos);
        } catch (cleanupError) {
          console.error('Failed to clean up new photos after error', cleanupError);
        }
      }
      throw innerError;
    }
  } catch (error) {
    next(error);
  }
});

router.get('/:storyId', async (req, res, next) => {
  try {
    const storyId = toObjectId(req.params.storyId);
    const db = getDb();
    const story = await db.collection(STORIES_COLLECTION).findOne({ _id: storyId });
    if (!story) {
      const error = new Error('Story not found.');
      error.status = 404;
      throw error;
    }
    res.json(serializeStory(story, req));
  } catch (error) {
    next(error);
  }
});

router.get('/:storyId/photos/:photoId', async (req, res, next) => {
  try {
    const storyId = toObjectId(req.params.storyId);
    const photoId = toObjectId(req.params.photoId);

    const db = getDb();
    const story = await db.collection(STORIES_COLLECTION).findOne({ _id: storyId, 'photos.id': photoId });
    if (!story) {
      const error = new Error('Photo not found for the requested story.');
      error.status = 404;
      throw error;
    }

    const photoMeta = story.photos.find((photo) => photo.id.equals(photoId));
    const bucket = getBucket();
    res.set('Content-Type', photoMeta?.contentType || 'application/octet-stream');
    bucket.openDownloadStream(photoId).pipe(res).on('error', next);
  } catch (error) {
    next(error);
  }
});

router.delete('/:storyId', async (req, res, next) => {
  try {
    const storyId = toObjectId(req.params.storyId);
    const target = (req.query.target || 'all').toString();
    const db = getDb();
    const stories = db.collection(STORIES_COLLECTION);
    const story = await stories.findOne({ _id: storyId });
    if (!story) {
      const error = new Error('Story not found.');
      error.status = 404;
      throw error;
    }

    if (target === 'photos') {
      await deleteImages(story.photos);
      await stories.updateOne({ _id: storyId }, {
        $set: {
          photos: [],
          story: null,
          updatedAt: new Date()
        }
      });
      return res.status(204).send();
    }

    if (target === 'prompt') {
      await stories.updateOne({ _id: storyId }, {
        $set: {
          prompt: null,
          updatedAt: new Date()
        }
      });
      return res.status(204).send();
    }

    if (target === 'story') {
      await stories.updateOne({ _id: storyId }, {
        $set: {
          story: null,
          updatedAt: new Date()
        }
      });
      return res.status(204).send();
    }

    await deleteImages(story.photos);
    await stories.deleteOne({ _id: storyId });
    res.status(204).send();
  } catch (error) {
    next(error);
  }
});

export default router;
