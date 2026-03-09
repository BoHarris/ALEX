import { motion } from "framer-motion";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.3,
    },
  },
};

const letterVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 },
};

const subtitleVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { delay: 2, duration: 1 },
  },
};

const AnimatedLandingHeader = () => {
  const header = "Welcome to Alex.ai".split("");

  return (
    <div className="text-center mt-16">
      <motion.h1
        className="text-4xl sm:text-5xl font-bold text-white"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {header.map((char, index) => (
          <motion.span
            key={index}
            variants={letterVariants}
            className={char === "." ? "text-red-400" : ""}
          >
            {char}
          </motion.span>
        ))}
      </motion.h1>

      <motion.p
        className="text-gray-400 mt-4 text-lg"
        variants={subtitleVariants}
        initial="hidden"
        animate="visible"
      >
        Scan. Redact. Protect.
      </motion.p>
    </div>
  );
};

export default AnimatedLandingHeader;
