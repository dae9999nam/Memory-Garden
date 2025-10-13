import express from 'express';
import dotenv from 'dotenv';
import storiesRouter from './routes/stories.js';
import { connectMongo } from './db/mongo.js';
import { multerErrorHandler } from './middleware/uploads.js';

dotenv.config();

const app = express();
app.use(express.json({ limit: '10mb' }));

app.use('/stories', storiesRouter);
app.use(multerErrorHandler);

app.use((err, req, res, next) => {
  if (res.headersSent) {
    return next(err);
  }
  const status = err.status || 500;
  res.status(status).json({
    error: err.name || 'ServerError',
    message: err.message,
    details: err.details || undefined
  });
});

const port = process.env.PORT || 8000;

connectMongo()
  .then(() => {
    app.listen(port, () => {
      console.log(`Memory Garden API listening on port ${port}`);
    });
  })
  .catch((error) => {
    console.error('Failed to start server', error);
    process.exit(1);
  });

export default app;
