import multer from 'multer';

const storage = multer.memoryStorage();

const upload = multer({
  storage,
  limits: {
    files: 10,
    fileSize: 15 * 1024 * 1024
  },
  fileFilter: (req, file, cb) => {
    if (!file.mimetype.startsWith('image/')) {
      return cb(new Error('Only image uploads are supported.'));
    }
    cb(null, true);
  }
});

export const uploadImages = upload.array('photos', 10);

export function multerErrorHandler (err, req, res, next) {
  if (err instanceof multer.MulterError || err.message === 'Only image uploads are supported.') {
    err.status = err.status || 400;
  }
  next(err);
}
