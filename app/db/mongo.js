import { MongoClient, GridFSBucket, ObjectId } from 'mongodb';

let client;
let database;
let bucket;

export async function connectMongo () {
  if (database) {
    return database;
  }

  const uri = process.env.MONGODB_URI;
  const dbName = process.env.MONGODB_DB || 'memory-garden';

  if (!uri) {
    throw new Error('MONGODB_URI environment variable is required');
  }

  client = new MongoClient(uri, {
    maxPoolSize: 10
  });

  await client.connect();
  database = client.db(dbName);
  bucket = new GridFSBucket(database, { bucketName: 'storyImages' });

  return database;
}

export function getDb () {
  if (!database) {
    throw new Error('Database not initialised. Call connectMongo() first.');
  }
  return database;
}

export function getBucket () {
  if (!bucket) {
    throw new Error('GridFS bucket not initialised. Call connectMongo() first.');
  }
  return bucket;
}

export function toObjectId (value) {
  if (value instanceof ObjectId) {
    return value;
  }
  if (!ObjectId.isValid(value)) {
    const error = new Error('Invalid identifier provided');
    error.status = 400;
    throw error;
  }
  return new ObjectId(value);
}

export async function disconnectMongo () {
  if (client) {
    await client.close();
    client = null;
    database = null;
    bucket = null;
  }
}
